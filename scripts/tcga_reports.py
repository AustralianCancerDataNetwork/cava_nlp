# Script to combine the raw reports with metadata
# - Raw reports: https://github.com/tatonetti-lab/tcga-path-reports
# - Metadata: https://github.com/tatonetti-lab/tnm-stage-classifier/tree/main/TCGA_Metadata
# More information can be found here: https://www.codabench.org/competitions/14070/
# Information about metadata:
#   - T: Primary tumor stage (T1, T2, T3, T4)
#   - N: Lymph node involvement (N0, N1, N2, N3)
#   - M: Metastasis status (M0, M1)

import argparse
import pathlib
import pickle
import pandas as pd
import dataclasses
import inspect
from sklearn.metrics import f1_score, precision_recall_fscore_support
from typing import Union, Optional, Generator

from cava_nlp import CaVaLang
from cava_nlp.regex_matcher import REGEX_SPAN_KEY
from prompt_spec import PromptTemplate
from omop_spires import DEFAULT_INSTRUCTOR_MODEL, DEFAULT_EMBEDDING_MODEL
from omop_spires.client import InstructorClient, LLMClient
from omop_spires.engine import InstructorEngine, SPIRESEngineWrapper
from omop_spires.loader import get_prompt_details, get_template_details

import logging
logger = logging.getLogger(__name__)

def _add_parser_tcga_predict_staging(subparsers):
    subparser = subparsers.add_parser(
        "predict_staging",
        help="Predict staging information from TCGA pathology reports using an InstructorEngine based on the OMOP SPIRES framework.",
    )
    subparser.add_argument("--input_path", type=str, required=True, help="Directory containing processed pathology reports and metadata files.")
    subparser.add_argument("--output_path", type=str, required=True, help="Path to the output file where processed data will be written.")
    subparser.add_argument(
        "-t",
        "--template",
        type=str,
        help="Name of the template YAML file defining the extraction schema.",
        default="omop_staging.yaml"
    )
    subparser.add_argument(
        "-m",
        "--model",
        type=str,
        default=DEFAULT_INSTRUCTOR_MODEL,
        help="Model to use for Instructor extraction.",
    )

    subparser.add_argument(
        "--model_embedding",
        type=str,
        default=DEFAULT_EMBEDDING_MODEL,
        help="Model to use for embedding generation.",
    )

    subparser.add_argument(
        "--model_api_base",
        type=str,
        required=True,
        help="Base URL for LLM access (e.g., http://localhost:11434/v1). Used for instructor model and embedding model.",
    )

    subparser.add_argument(
        "--system_message",
        type=str,
        help="System message to provide context to the LLM.",
        default=(
            "You are a helpful assistant that extracts clinical entities from "
            "text according to the provided schema."
        ),
    )

    subparser.add_argument(
        "-p",
        "--promptfile",
        type=str,
        help="Name of the custom prompt file (YAML).",
        default="omop_staging_prompt.yaml",
    )

    subparser.add_argument(
        "--show_logging",
        action="store_true",
        help="Show LightLLM/backend debug information.",
    )

    subparser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity: -v for INFO, -vv for DEBUG.",
    )
    subparser.set_defaults(func=predict_tcga_reports_staging)

def _add_parser_tcga_eval_staging(subparsers) -> None:
    subparser = subparsers.add_parser(
        "eval_staging",
        help="Evaluate staging predictions against true labels for tumour stage, lymph node involvement, and metastasis status.",
    )
    subparser.add_argument(
        "--input_path", 
        type=str, 
        required=True, 
        help="Path to the processed data file containing predictions and true labels."
    )
    subparser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity: -v for INFO, -vv for DEBUG.",
    )

    subparser.add_argument(
        "--show_logging",
        action="store_true",
        help="Show LightLLM/backend debug information.",
    )

    subparser.set_defaults(func=evaluate_tcga_predictions)

def get_parser():

    argparser = argparse.ArgumentParser(description="Cava-NLP TCGA Reports Processing Script")
    subparsers = argparser.add_subparsers(dest="command", required=True)

    # Predict parser staging
    _add_parser_tcga_predict_staging(subparsers)

    # Evaluation parser staging
    _add_parser_tcga_eval_staging(subparsers)
    
    return argparser

def configure_logging_level(verbosity: int, reduce_logging: bool = True) -> None:
    """Configure global logging."""
    level_map = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}
    log_level = level_map.get(min(verbosity, 2), logging.DEBUG)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )

    if reduce_logging:
        existing_loggers = [
            logging.getLogger(name) for name in logging.root.manager.loggerDict
        ]
        exempt_loggers = ["omop_spires", "ontogpt", "instructor", "cava_nlp"]
        for logger_instance in existing_loggers:
            if not any(
                logger_instance.name.startswith(exempt) for exempt in exempt_loggers
            ):
                logger_instance.setLevel(logging.WARNING)

@dataclasses.dataclass(frozen=True)
class TCGAItem:
    text: str
    tumour: str
    lymph_node: str
    metastasis: str
    cancer_type: str

    @classmethod
    def from_dict(cls, env):      
        return cls(**{
            k: v for k, v in env.items() 
            if k in inspect.signature(cls).parameters
        })
    

KEY_TUMOUR = "tumour"
KEY_METASTASIS = "metastasis"
KEY_LYMPH_NODE = "lymph_node"
KEY_CANCER_TYPE = "cancer_type"
KEY_REGEX_CAUGHT = "regex_caught"

def get_pred_key(col_name: str) -> str:
    return f"p_{col_name}"

def tcga_item_iterator(pd_df: pd.DataFrame) -> Generator[tuple[int, TCGAItem], None, None]:
    for row_idx, row in pd_df.iterrows():
        assert isinstance(row_idx, int)
        yield row_idx, TCGAItem.from_dict(row.to_dict())

def process_tcga_reports(input_path, output_path, overwrite: bool = False) -> pd.DataFrame:
    input_base_dir = pathlib.Path(input_path)
    output_path = pathlib.Path(output_path)

    if output_path.exists():
        if overwrite:
            logger.info(f"Output file {output_path} already exists. Overwriting as per the 'overwrite' flag.")
            output_path.unlink()
        else:
            logger.info(f"Output file {output_path} already exists. Loading existing data.")
            return pd.read_csv(output_path)

    required_files = {
        "reports": {
            "filename": "TCGA_Reports.csv",
            "description": "CSV file containing the raw pathology reports.",
            "url": "https://github.com/tatonetti-lab/tcga-path-reports/blob/main/TCGA_Reports.csv.zip"
        },
        "tumour": {
            "filename": "TCGA_T14_patients.csv",
            "description": "CSV file containing metadata about the primary tumour stage (T).",
            "url": "https://github.com/tatonetti-lab/tnm-stage-classifier/blob/main/TCGA_Metadata/TCGA_T14_patients.csv"
        },
        "lymph_node": {
            "filename": "TCGA_N03_patients.csv",
            "description": "CSV file containing metadata about lymph node involvement (N).",
            "url": "https://github.com/tatonetti-lab/tnm-stage-classifier/blob/main/TCGA_Metadata/TCGA_N03_patients.csv"
        },
        "metastasis": {
            "filename": "TCGA_M01_patients.csv",
            "description": "CSV file containing metadata about metastasis status (M).",
            "url": "https://github.com/tatonetti-lab/tnm-stage-classifier/blob/main/TCGA_Metadata/TCGA_M01_patients.csv"
        },
        "cancer_types": {
            "filename": "TCGA_cancer_types_binary.p",
            "description": "Pickle file containing a dictionary mapping patient IDs to their cancer types.",
            "url": "https://github.com/tatonetti-lab/tnm-stage-classifier/blob/main/TCGA_Metadata/TCGA_cancer_types_binary.p",
        }
    }

    for key, file_info in required_files.items():
        file_path = input_base_dir / file_info["filename"]
        if not file_path.exists():
            raise FileNotFoundError(
                (
                    f"Missing file: '{file_info['filename']}'\n",
                    f"Description: {file_info['description']}\n",
                    f"Download URL: {file_info['url']}\n",
                )
            )
        
    df_reports = pd.read_csv(input_base_dir / required_files["reports"]["filename"])
    df_tumour = pd.read_csv(input_base_dir / required_files["tumour"]["filename"])
    df_lymph_node = pd.read_csv(input_base_dir / required_files["lymph_node"]["filename"])
    df_metastasis = pd.read_csv(input_base_dir / required_files["metastasis"]["filename"])
    df_cancer_types = pickle.load(open(input_base_dir / required_files["cancer_types"]["filename"], "rb"))
    
    # Add patient_id from the file-name to df_reports
    df_reports["patient_id"] = df_reports["patient_filename"].apply(lambda x: x.split(".")[0])
    assert len(df_reports["patient_id"].unique()) == len(df_reports), "Expected patient_id to be unique in reports data"

    # Now we can merge
    df_reports_with_metadata = df_reports.merge(
        df_tumour[['case_submitter_id', 'ajcc_pathologic_t']].rename(
            columns={'ajcc_pathologic_t': KEY_TUMOUR}
        ),
        left_on='patient_id', 
        right_on='case_submitter_id', 
        how='left'
    ).drop(columns=['case_submitter_id'])

    df_reports_with_metadata = df_reports_with_metadata.merge(
        df_lymph_node[['case_submitter_id', 'ajcc_pathologic_n']].rename(
            columns={'ajcc_pathologic_n': KEY_LYMPH_NODE}
        ),
        left_on='patient_id', 
        right_on='case_submitter_id', 
        how='left'
    ).drop(columns=['case_submitter_id'])

    df_reports_with_metadata = df_reports_with_metadata.merge(
        df_metastasis[['case_submitter_id', 'ajcc_pathologic_m']].rename(
            columns={'ajcc_pathologic_m': KEY_METASTASIS}
        ),
        left_on='patient_id', 
        right_on='case_submitter_id', 
        how='left'
    ).drop(columns=['case_submitter_id'])

    df_reports_with_metadata = df_reports_with_metadata.merge(
        df_cancer_types[["patient", "type"]].rename(
            columns={"patient": "patient_id", "type": KEY_CANCER_TYPE}
        ), 
        left_on="patient_id", 
        right_on="patient_id", 
        how="left"
    ).drop(columns=["patient_id"])

    # Drop entries with missing metadata
    df_final = df_reports_with_metadata.dropna(subset=[KEY_TUMOUR, KEY_LYMPH_NODE, KEY_METASTASIS, KEY_CANCER_TYPE])
    logger.info(f"Final dataset contains {len(df_final)} entries after merging and dropping missing metadata.")

    df_final.to_csv(output_path, index=False)
    logger.info(f"Combined data saved to {output_path}")

    return df_final

def _create_instructor_engine(
    template: Union[str, pathlib.Path],
    promptfile: Optional[str],
    model: str,
    model_api_base: str,
    model_embedding: str,
    system_message: Optional[str] = None,
) -> tuple[InstructorEngine, PromptTemplate]:

    # Prepare OMOP SPIRES
    template_details, template_path = get_template_details(str(template))
    prompt_template, _ = get_prompt_details(
        promptfile=promptfile, template_path=template_path
    )

    if (
        prompt_template is not None
        and prompt_template.system is not None
        and system_message is not None
    ):
        logger.warning(
            "Both prompt template and system message provided. "
            "Using system message from prompt template."
        )
        system_message = prompt_template.system
    assert system_message is not None, "System message must be provided either through the prompt template or as a separate argument."

    instructor_client = InstructorClient(
        model=model,
        api_base=model_api_base,
        system_message=system_message,
    )

    embedding_client = LLMClient(
        model=model_embedding,
        api_base=model_api_base,
        system_message=""
    )

    engine = InstructorEngine(
        client=instructor_client,
        embedding_client=embedding_client,
        template_details=template_details,
    )

    return engine, prompt_template  # type: ignore

def predict_tcga_reports_staging(
    input_path: str, 
    output_path: str, 
    model: str,
    model_api_base: str,
    model_embedding: str,
    system_message: str,
    max_predictions: int = 500,
    **kwargs
):
    """Predicts staging information from TCGA pathology reports using an InstructorEngine based on the OMOP SPIRES framework. The function processes the raw reports, extracts relevant metadata, and evaluates the predictions against the true labels for tumour stage, lymph node involvement, and metastasis status.
    
    Notes
    -----
    - Challenge information: https://www.codabench.org/competitions/14070/
    """

    from omop_spires.templates.modules.omop_staging import CancerDiagnosis, Document

    
    engine, prompt_template = _create_instructor_engine(
        template="omop_staging.yaml",
        promptfile="omop_staging_prompt.yaml",
        model=model,
        model_api_base=model_api_base,
        model_embedding=model_embedding,
        system_message=system_message,
    )
    
    # Data
    pd_tcga = process_tcga_reports(input_path, output_path, overwrite=False)
    # Only get the ones that are missing the predictions
    target_col = get_pred_key(KEY_TUMOUR)
    if target_col in pd_tcga.columns:
        # Column exists, filter normally
        df_to_be_processed = pd_tcga[pd_tcga[target_col].isnull()].drop_duplicates(subset=['text'])
    else:
        df_to_be_processed = pd_tcga.drop_duplicates(subset=['text'])

    # NLP
    nlp = CaVaLang()
    nlp.add_pipe(
        "regex_matcher",
        config={
            "pattern_config": None,
            "component_names": "Stage"
        },
    )

    for num_predictions, (row_idx, val) in enumerate(df_to_be_processed['text'].items()):
        if num_predictions >= max_predictions:
            logger.info(f"Reached maximum number of predictions ({max_predictions}). Stopping further predictions.")
            break

        assert isinstance(row_idx, int), f"Expected row index to be an integer, got {type(row_idx)}"
        doc = nlp(val)
        spans = doc.spans.get(REGEX_SPAN_KEY, [])

        regex_caught = bool(spans)
        try:
            _prediction = engine.extract_from_text(
                text=doc.text,
                prompt_template=prompt_template,
                show_prompt=False
            )
        except Exception as e:
            logger.exception(f"Error during extraction for row index {row_idx}. Skipping this entry. {e}")
            continue

        extracted_object = _prediction.extracted_object
        assert isinstance(extracted_object, Document), "Expected extracted object to be a document."
        cancer_diagnoses = extracted_object.cancer_diagnoses

        if cancer_diagnoses:
            cancer_diagnosis = next(iter(cancer_diagnoses)) # Just a single one
            assert isinstance(cancer_diagnosis, CancerDiagnosis), f"Expected extracted object to be an instance of CancerDiagnosis, got {type(cancer_diagnosis)}"
            metastatis = cancer_diagnosis.metastasis.concept_name if cancer_diagnosis.metastasis else None
            lymph_node = cancer_diagnosis.lymph_node.concept_name if cancer_diagnosis.lymph_node else None
            tumour = cancer_diagnosis.tumour.concept_name if cancer_diagnosis.tumour else None
            cancer_type = cancer_diagnosis.concept_name

            for col_name, pred in zip(
                (KEY_TUMOUR, KEY_LYMPH_NODE, KEY_METASTASIS, KEY_CANCER_TYPE), 
                (tumour, lymph_node, metastatis, cancer_type)):
                pred_key = get_pred_key(col_name)
                pd_tcga.at[row_idx, pred_key] = pred

            # Also add the regex-caught information
            pd_tcga.at[row_idx, KEY_REGEX_CAUGHT] = regex_caught
            
            # Save the predictions after each row is processed to avoid losing data in case of interruptions
            pd_tcga.to_csv(output_path, index=False)
    
    # Save the predictions
    pd_tcga.to_csv(output_path, index=False)
     

def evaluate_tcga_predictions(
    input_path: Union[str, pathlib.Path],
    **kwargs
):
    """Evaluates staging predictions against true labels for tumour stage, lymph node involvement, and metastasis status. This function compares the predicted values with the true labels in the processed data file and calculates evaluation metrics such as accuracy, precision, recall, and F1-score for each of the staging components (T, N, M). The results can be used to assess the performance of the prediction model on the TCGA pathology reports.
    
    Notes
    -----
    - Evaluation implementation is pending and will be added in a future update.
    """

    df_tcga = pd.read_csv(input_path)

    predicted_staging = df_tcga[df_tcga[get_pred_key(KEY_TUMOUR)].notnull()]
    predicted_staging_with_regex = predicted_staging[predicted_staging[KEY_REGEX_CAUGHT] == True]

    results = []

    for _df, df_name in zip([predicted_staging, predicted_staging_with_regex], ["all", "regex"]):
        for col in [KEY_TUMOUR, KEY_LYMPH_NODE, KEY_METASTASIS]:
            pred_col = get_pred_key(col)
            
            if pred_col not in _df.columns:
                continue
            
            # Not nan values only
            _df = _df.dropna(subset=[col, pred_col])
            gt = _df[col].astype(str)
            pred = _df[pred_col].astype(str)
            labels = list(sorted(set(df_tcga[col].dropna().unique().astype(str)) | set(_df[pred_col].dropna().unique().astype(str))))

            precision_vals, recall_vals, f1_vals, support_vals = precision_recall_fscore_support(
                gt, pred, labels=labels, zero_division=0
            )

            # Create a record for each label
            for label, f1, precision, recall, support in zip(labels, f1_vals, precision_vals, recall_vals, support_vals): # type: ignore
                results.append({
                    "Dataset": df_name,
                    "Category": col,
                    "Label": label,
                    "f1": round(f1, 3),
                    "precision": round(precision, 3), 
                    "recall": round(recall, 3),
                    "Num GT": int(support),
                })

    # Transform to a beautiful DataFrame
    report_df = pd.DataFrame(results)

    # Optional: Pivot it for an even better "Comparison View"
    comparison_view = report_df.pivot_table(
        index=["Category", "Label"], 
        columns="Dataset", 
        values=("f1", "precision", "recall", "Num GT")
    )
    print("Evaluation Report:")
    print(comparison_view)

if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    configure_logging_level(args.verbose, reduce_logging=not args.show_logging)

    args.func(**vars(args))
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

from typing import Generator

from cava_nlp import CaVaLang
from cava_nlp.regex_matcher import REGEX_SPAN_KEY

import logging
logger = logging.getLogger(__name__)

def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

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

def tcga_item_iterator(pd_df: pd.DataFrame) -> Generator[TCGAItem, None, None]:
    for _, row in pd_df.iterrows():
        yield TCGAItem.from_dict(row.to_dict())

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
            columns={'ajcc_pathologic_t': 'tumour'}
        ),
        left_on='patient_id', 
        right_on='case_submitter_id', 
        how='left'
    ).drop(columns=['case_submitter_id'])

    df_reports_with_metadata = df_reports_with_metadata.merge(
        df_lymph_node[['case_submitter_id', 'ajcc_pathologic_n']].rename(
            columns={'ajcc_pathologic_n': 'lymph_node'}
        ),
        left_on='patient_id', 
        right_on='case_submitter_id', 
        how='left'
    ).drop(columns=['case_submitter_id'])

    df_reports_with_metadata = df_reports_with_metadata.merge(
        df_metastasis[['case_submitter_id', 'ajcc_pathologic_m']].rename(
            columns={'ajcc_pathologic_m': 'metastasis'}
        ),
        left_on='patient_id', 
        right_on='case_submitter_id', 
        how='left'
    ).drop(columns=['case_submitter_id'])

    df_reports_with_metadata = df_reports_with_metadata.merge(
        df_cancer_types[["patient", "type"]].rename(
            columns={"patient": "patient_id", "type": "cancer_type"}
        ), 
        left_on="patient_id", 
        right_on="patient_id", 
        how="left"
    ).drop(columns=["patient_id"])

    # Drop entries with missing metadata
    df_final = df_reports_with_metadata.dropna(subset=['tumour', 'lymph_node', 'metastasis', "cancer_type"])
    logger.info(f"Final dataset contains {len(df_final)} entries after merging and dropping missing metadata.")

    df_final.to_csv(output_path, index=False)
    logger.info(f"Combined data saved to {output_path}")

    return df_final
    

def tcga_reports_prediction(
    input_path: str, 
    output_path: str, 
):
    
    pd_tcga = process_tcga_reports(input_path, output_path, overwrite=False)

    pd_tcga_iterator = tcga_item_iterator(pd_tcga)

    nlp = CaVaLang()
    nlp.add_pipe(
        "regex_matcher",
        config={
            "pattern_config": None,
            "component_names": "Stage"
        },
    )

    for tcga_item in pd_tcga_iterator:
        doc = nlp(tcga_item.text)
        spans = doc.spans.get(REGEX_SPAN_KEY, [])
        for span in spans:
            four = 4

    # Process the data into chunks and then put it into an LLM pipeline that extracts stage or something?
    # TODO: facotry with the CavaLang bit to load it instead of manually adding it 
    four = 4


if __name__ == "__main__":

    configure_logging()

    argparse = argparse.ArgumentParser(description="Append metadata to TCGA reports and save the combined data to a new file.")
    argparse.add_argument("--input_path", type=str, required=True, help="Directory containing processed pathology reports and metadata files.")
    argparse.add_argument("--output_path", type=str, required=True, help="Path to the output file where processed data will be written.")
    args = argparse.parse_args()
    tcga_reports_prediction(args.input_path, args.output_path)
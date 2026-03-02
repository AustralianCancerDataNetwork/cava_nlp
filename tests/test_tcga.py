# https://github.com/tatonetti-lab/tcga-path-reports
from cava_nlp import CaVaLang
from cava_nlp.regex_matcher import REGEX_SPAN_KEY

from ..scripts.tcga_reports import tcga_item_iterator, TCGAItem, process_tcga_reports

import pytest
from functools import partial
import pathlib

from typing import Generator
from collections.abc import Callable



@pytest.fixture(scope="session")
def load_tcga_data() -> Callable[[], Generator[TCGAItem, None, None]]:

    this_file_path = pathlib.Path(__file__).parent
    input_path = this_file_path.parent / "input" / "tcga"
    output_path = this_file_path.parent / "output" / "tcga_reports.csv"

    df = process_tcga_reports(
        input_path=input_path,
        output_path=output_path,
        overwrite=False
    )

    callable_ = partial(
        tcga_item_iterator,
        pd_df=df
    )
    return callable_

class TestTCGA:
    def test_regex(self, load_tcga_data, staging_data):

        nlp = CaVaLang()
        nlp.add_pipe(
            "regex_matcher",
            config={
                "pattern_config": None,
                "component_names": "Stage"
            },
        )

        for item in load_tcga_data():
            if isinstance(item, TCGAItem):
                doc_str = item.text
            elif isinstance(item, str):
                doc_str = item
            else:
                raise ValueError(f"Expected item to be either dict or str, got {type(item)}")
            assert isinstance(doc_str, str), f"Expected 'text' field to be a string, got {type(doc_str)}"
            doc = nlp(doc_str)
            spans = doc.spans.get(REGEX_SPAN_KEY, [])
            if spans:
                four = 4
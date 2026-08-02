"""
machine_learning/train_test_split.py

Purpose: Splits the preprocessed feature/target data into training and
test sets using a strict chronological cutoff -- never a random
shuffle, since shuffling time series data would let the model "see the
future" during training (train on later dates, test on earlier ones)
and produce misleadingly good evaluation scores.
"""

from dataclasses import dataclass

import pandas as pd

from custom_exceptions import DataProcessingError
from machine_learning.data_preprocessing import PreprocessedData

DEFAULT_TEST_SIZE = 0.2


@dataclass
class SplitData:
    """Container for a chronological train/test split."""

    x_train: pd.DataFrame
    x_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series


def chronological_split(data: PreprocessedData, test_size: float = DEFAULT_TEST_SIZE) -> SplitData:
    """
    Split features/target chronologically: the earliest (1 - test_size)
    fraction of rows becomes the training set, the most recent
    `test_size` fraction becomes the (out-of-sample) test set.

    Raises:
        DataProcessingError: if test_size is out of range or too few rows result in either split.
    """
    if not (0.05 <= test_size <= 0.5):
        raise DataProcessingError("test_size must be between 0.05 and 0.5 for a meaningful train/test split.")

    total_rows = len(data.features)
    split_index = int(total_rows * (1 - test_size))

    x_train = data.features.iloc[:split_index]
    x_test = data.features.iloc[split_index:]
    y_train = data.target.iloc[:split_index]
    y_test = data.target.iloc[split_index:]

    if len(x_train) < 30 or len(x_test) < 10:
        raise DataProcessingError(
            f"Chronological split produced too few rows (train={len(x_train)}, test={len(x_test)}) "
            f"to train and evaluate a model reliably."
        )

    return SplitData(x_train=x_train, x_test=x_test, y_train=y_train, y_test=y_test)

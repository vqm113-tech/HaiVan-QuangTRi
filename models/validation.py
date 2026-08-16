"""
=========================================================
models/validation.py
HaiVan Forecast System 6.0
Model Validation
=========================================================
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(slots=True)
class ValidationResult:

    rmse: float

    mae: float

    bias: float

    mse: float

    correlation: float

    scatter_index: float

    nash_sutcliffe: float

    skill_score: float


class Validator:

    """
    Marine Forecast Validation
    """

    def rmse(self, obs, sim):

        obs = np.asarray(obs)
        sim = np.asarray(sim)

        return np.sqrt(
            np.mean(
                (obs - sim) ** 2
            )
        )

    def mae(self, obs, sim):

        return np.mean(
            np.abs(obs - sim)
        )

    def bias(self, obs, sim):

        return np.mean(
            sim - obs
        )

    def mse(self, obs, sim):

        return np.mean(
            (obs - sim) ** 2
        )

    def correlation(self, obs, sim):

        return np.corrcoef(
            obs,
            sim
        )[0, 1]

    def scatter_index(self, obs, sim):

        rmse = self.rmse(obs, sim)

        return rmse / np.mean(obs)

    def nash_sutcliffe(self, obs, sim):

        obs = np.asarray(obs)

        sim = np.asarray(sim)

        return 1 - (

            np.sum(

                (obs - sim) ** 2

            )

            /

            np.sum(

                (obs - obs.mean()) ** 2

            )

        )

    def skill_score(self, obs, sim):

        obs = np.asarray(obs)

        sim = np.asarray(sim)

        num = np.sum(

            (sim - obs) ** 2

        )

        den = np.sum(

            (

                np.abs(sim - obs.mean())

                +

                np.abs(obs - obs.mean())

            ) ** 2

        )

        return 1 - num / den

    def evaluate(self, obs, sim):

        return ValidationResult(

            rmse=self.rmse(obs, sim),

            mae=self.mae(obs, sim),

            bias=self.bias(obs, sim),

            mse=self.mse(obs, sim),

            correlation=self.correlation(obs, sim),

            scatter_index=self.scatter_index(obs, sim),

            nash_sutcliffe=self.nash_sutcliffe(obs, sim),

            skill_score=self.skill_score(obs, sim)

        )
import hydra
from omegaconf import OmegaConf

from pit_38_usd_schwab_calculator.config_store import Config
from pit_38_usd_schwab_calculator.pit_38_usd_schwab_calculator import (
    Pit38USDSchwabCalculator,
)


@hydra.main(config_path="conf", version_base=None)
def main(config: Config) -> None:
    config = OmegaConf.merge(Config(), config)
    Pit38USDSchwabCalculator(config).summarize()


if __name__ == "__main__":
    main()

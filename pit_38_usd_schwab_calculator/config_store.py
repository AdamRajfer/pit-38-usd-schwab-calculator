from dataclasses import dataclass, field

from hydra.core.config_store import ConfigStore


@dataclass
class FormatConfig:
    espp: str = "\033[38;5;208m"
    rs: str = "\033[35m"


@dataclass
class Config:
    path: str = ""
    employment_date: str = ""
    salary_gross_per_month: float = -1
    salary_net_per_month: float = -1
    format_config: FormatConfig = field(default_factory=FormatConfig)


cs = ConfigStore.instance()
cs.store(name="pit_38_usd_schwab_calculator", node=Config)

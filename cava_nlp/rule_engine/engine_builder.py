# import spacy
# from spacy.language import Language
# from pathlib import Path

# from cava_nlp.namespaces.core.loader import load_engine_config
# from cava_nlp.rule_engine.rule_engine import RuleEngine

# # @Language.factory("rule_engine")
# # def create_rule_engine(nlp, name, config):
# #     """Factory that produces a RuleEngine instance."""
# #     return RuleEngine(nlp, name, config)

# class EngineBuilder:
#     """
#     Pipeline builder that constructs a spaCy NLP object from engine_config.yaml.
#     """

#     def __init__(self, nlp, config_path=None):
#         if config_path:
#             self.config_path = Path(config_path).expanduser().resolve()
#         else:
#             self.config_path = (Path(__file__).parent / "config" / "default.yaml").resolve()

#         if not self.config_path.exists():
#             raise FileNotFoundError(
#                 f"Engine config not found: {self.config_path}\n"
#                 "Provide a valid path or ensure engine_config.yaml exists next to engine_builder.py."
#             )
#         self.config = load_engine_config(self.config_path)
#         self.nlp = nlp

#     def _add_components(self):
#         """Add components defined in config['components']."""
#         components = self.config.get("components", {})

#         for name, comp_cfg in components.items():
#             factory = comp_cfg.get("factory")
#             if not factory:
#                 raise ValueError(f"Component '{name}' missing required 'factory' field.")

#             config = comp_cfg.get("config", {})
#             before = comp_cfg.get("before")
#             after = comp_cfg.get("after")

#             print(f"[EngineBuilder] Adding component '{name}' (factory={factory})")

#             self.nlp.add_pipe(
#                 factory,
#                 name=name,
#                 config=config,
#                 before=before,
#                 after=after,
#             )

#     def build(self):
#         self._add_components()
#         return self.nlp


# def build_engine(nlp, config_path: str):
#     """Shortcut: build engine in one call."""
#     builder = EngineBuilder(nlp, config_path)
#     return builder.build()

from argparse import ArgumentParser, ArgumentTypeError
import unittest

from mods.arguments import parse_bool


class BooleanArgumentTests(unittest.TestCase):
    def test_accepts_existing_spellings_case_insensitively(self):
        for value in ("y", "yes", "t", "true", "on", "1"):
            self.assertIs(parse_bool(value.upper()), True)
        for value in ("n", "no", "f", "false", "off", "0"):
            self.assertIs(parse_bool(value.upper()), False)

    def test_invalid_value_is_an_argument_error(self):
        with self.assertRaises(ArgumentTypeError):
            parse_bool("maybe")

    def test_parser_keeps_defaults_and_reads_explicit_false(self):
        parser = ArgumentParser()
        parser.add_argument("--https", type=parse_bool, default=False)
        parser.add_argument("--httpsSelfSigned", type=parse_bool, default=True)
        self.assertIs(parser.parse_args([]).httpsSelfSigned, True)
        self.assertIs(parser.parse_args(["--httpsSelfSigned", "false"]).httpsSelfSigned, False)

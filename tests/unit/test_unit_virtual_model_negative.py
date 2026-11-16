import pytest

from ozonenv.core.ModelMaker import BaseModelMaker


def make_maker(fields_parser: dict = None) -> BaseModelMaker:
    return BaseModelMaker("virtual_test", fields_parser=fields_parser or {})


class TestVirtualModelNegativeNumbers:
    @pytest.mark.parametrize(
        "raw,expected_type,expected_value",
        [
            ("-5", int, -5),
            ("-1446.16", float, -1446.16),
            ("-0.5", float, -0.5),
            ("-.5", float, -0.5),
            ("+7", int, 7),
            (-5, int, -5),
            (-1446.16, float, -1446.16),
            (-1e-07, float, -1e-07),
            # positive values keep working as before
            ("5", int, 5),
            ("1446.16", float, 1446.16),
            (0.0, float, 0.0),
        ],
    )
    def test_parse_make_field_keeps_sign(
        self, raw, expected_type, expected_value
    ):
        ftype, value = make_maker().parse_make_field(raw, "importo")
        assert ftype is expected_type
        assert type(value) is expected_type
        assert value == expected_value

    def test_non_numeric_values_are_not_touched(self):
        maker = make_maker()
        assert maker.parse_make_field("2022-05-23", "d") == (
            str,
            "2022-05-23",
        )
        assert maker.parse_make_field("abc-12", "c") == (str, "abc-12")
        assert maker.parse_make_field("true", "b") == (bool, True)
        assert maker.parse_make_field("m.bianchi", "u") == (str, "m.bianchi")

    def test_fields_parser_negative(self):
        maker = make_maker(
            {"saldo": {"type": "float"}, "qta": {"type": "int"}}
        )
        assert maker.parse_make_field("-10.25", "saldo") == (float, -10.25)
        assert maker.parse_make_field("-3", "qta") == (int, -3)

    def test_virtual_model_from_data_dict(self):
        maker = make_maker()
        maker.from_data_dict(
            {
                "rec_name": "virtual.negative",
                "saldo": "-1446.16",
                "qta": "-3",
                "sconto": -12.5,
                "riga": {"importo": "-289.23", "aliquota": "-20"},
                "righe": [
                    {"importo": "-1.5", "nr": "1"},
                    {"importo": "2.5", "nr": "-2"},
                ],
            }
        )
        assert maker.virtual is True
        doc = maker.new({"rec_name": "virtual.negative"})
        assert doc.saldo == -1446.16
        assert doc.qta == -3
        assert doc.sconto == -12.5
        assert doc.riga.get("importo") == -289.23
        assert doc.riga.get("aliquota") == -20
        assert doc.righe[0].get("importo") == -1.5
        assert doc.righe[1].get("nr") == -2
        # negative index reads from the end of a list
        assert doc.get("righe.-1.importo") == 2.5
        assert doc.get("righe.-2.importo") == -1.5
        assert doc.get("righe.0.importo") == -1.5

    def test_virtual_model_new_with_negative_payload(self):
        maker = make_maker()
        maker.from_data_dict({"rec_name": "virtual.negative", "saldo": "10.5"})
        doc = maker.new({"rec_name": "virtual.negative", "saldo": "-99.9"})
        assert doc.saldo == -99.9

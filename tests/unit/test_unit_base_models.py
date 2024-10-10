from ozonenv.core.BaseModels import DataReturn


class TestDataReturn:
    def test_default_initialization(self):
        """Test default initialization of DataReturn"""
        result = DataReturn()

        assert result.data is None  # data should default to None
        assert result.fail is False  # fail should default to False
        assert result.msg == ""  # msg should default to an empty string

    def test_custom_initialization(self):
        """Test custom initialization of DataReturn with various types"""
        result = DataReturn(data=42, fail=True, msg="Custom message")

        assert result.data == 42
        assert result.fail is True
        assert result.msg == "Custom message"

    def test_list_data(self):
        """Test using a list as the data"""
        data = [1, 2, 3]
        result = DataReturn(data=data)

        assert result.data == data
        assert result.data[0] == 1

    def test_dict_data(self):
        """Test using a dictionary as the data"""
        data = {"key": "value"}
        result = DataReturn(data=data)

        assert result.data == data
        assert result.data["key"] == "value"

    def test_none_data(self):
        """Test explicitly passing None to data"""
        result = DataReturn(data=None, fail=False, msg="No data")

        assert result.data is None
        assert result.fail is False
        assert result.msg == "No data"

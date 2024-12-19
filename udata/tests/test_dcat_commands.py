import pytest


@pytest.mark.usefixtures("clean_db")
class ParseUrlCommandTest:
    def test_parse_url(self, cli, requests_mock, caplog) -> None:
        logs = []

        def mock_echo(message: str) -> None:
            logs.append(message)

        local_file: str = "./udata/harvest/tests/dcat/sig.oreme.rdf"
        # This mock_url is to make requests' url parsing happy, but the mock will return the local file content.
        mock_url = "https://example.com/sig.oreme.rdf"
        with open(local_file, "r") as test_rdf_file:
            requests_mock.get(mock_url, text=test_rdf_file.read())
            requests_mock.head(mock_url, text="sig.oreme.rdf")
        dataset_id = "0437a976-cff1-4fa6-807a-c23006df2f8f"
        result = cli(
            "dcat",
            "parse-url",
            mock_url,
            "--rid",
            dataset_id,
        )
        assert "Dataset is valid" in result.stdout

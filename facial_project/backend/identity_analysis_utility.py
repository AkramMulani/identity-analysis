import requests


class IdentityAnalysisUtility:

    def __init__(self,
                 base_url="http://localhost:8080/api/fingerprint"):
        self.base_url = base_url

    def extractFingerData(self, imageFilePath):

        with open(imageFilePath, "rb") as file:

            files = {
                "file": file
            }

            response = requests.post(
                f"{self.base_url}/extract",
                files=files,
                timeout=30
            )

        response.raise_for_status()

        data = response.json()

        return data["template"]

    def verifyFingerData(self,
                         probeTemplate,
                         candidateTemplate):

        payload = {
            "probeTemplate": probeTemplate,
            "candidateTemplate": candidateTemplate
        }

        response = requests.post(
            f"{self.base_url}/verify",
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        return response.json()
    
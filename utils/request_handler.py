import requests
from termcolor import colored

__HEADERS = {
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9",
    "referer": "instagram.com",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "x-asbd-id": "129477",
    "x-ig-app-id": "936619743392459",
    "x-ig-www-claim": "0",
    "x-requested-with": "XMLHttpRequest",
}
__BASE_API_URL = "https://www.instagram.com/api/v1"
__BASE_DM_URL = f"{__BASE_API_URL}/direct_v2"

__sessionid: str = ""

number_of_requests: int = 0


def set_sessionid(sessionid: str):
    global __sessionid
    __sessionid = sessionid


def get_request(url: str, *, verbose: bool = False, return_json: bool = True) -> dict | requests.Response:
    global number_of_requests
    number_of_requests += 1

    if not url.startswith(__BASE_API_URL) or not url.startswith(__BASE_DM_URL):
        url = f"{__BASE_DM_URL}{url}"

    response = requests.get(url=url, headers=__HEADERS, cookies={
        "sessionid": __sessionid
    })

    if not response.ok:
        # If the text of the error is "Oops, an error occurred.", try again as Instagram's private API is volatile af
        if response.text.startswith("Oops, an error occurred."):
            if verbose:
                print(colored("[-] Instagram API threw weird 500. Trying again..."))

            return get_request(url, verbose=verbose, return_json=return_json)

        raise Exception(f"Request failed with status code {response.status_code} - {response.text}")

    if return_json:
        return response.json()

    return response

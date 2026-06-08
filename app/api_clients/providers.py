from app.api_clients.adobe import AdobeFireflyClient, AdobePhotoshopClient
from app.api_clients.photoroom import PhotoRoomClient


def provider_status() -> dict:
    return {
        "providers": [
            PhotoRoomClient().status(),
            AdobeFireflyClient().status(),
            AdobePhotoshopClient().status(),
        ]
    }

import json
import logging
from typing import Any, Dict, FrozenSet, Optional

from omemo.storage import Just, Maybe, Nothing, Storage
from omemo.types import DeviceInformation, JSONType

from slixmpp_omemo import TrustLevel, XEP_0384


from slixmpp.plugins import register_plugin  # type: ignore[attr-defined]

log = logging.getLogger(__name__)

class StorageImpl(Storage):
    """
    storage implementation that stores all data in a single JSON file.
    Copied from https://github.com/Syndace/slixmpp-omemo/tree/main/examples
    """
    def __init__(self, storage_dir) -> None:
        super().__init__()

        self.JSON_FILE = storage_dir
        self.__data: Dict[str, JSONType] = {}
        try:
            with open(self.JSON_FILE, encoding="utf8") as f:
                self.__data = json.load(f)
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    async def _load(self, key: str) -> Maybe[JSONType]:
        if key in self.__data:
            return Just(self.__data[key])

        return Nothing()

    async def _store(self, key: str, value: JSONType) -> None:
        self.__data[key] = value
        with open(self.JSON_FILE, "w", encoding="utf8") as f:
            json.dump(self.__data, f)

    async def _delete(self, key: str) -> None:
        self.__data.pop(key, None)
        with open(self.JSON_FILE, "w", encoding="utf8") as f:
            json.dump(self.__data, f)


class XEP_0384Impl(XEP_0384):  # pylint: disable=invalid-name
    """
    implementation of the OMEMO plugin for Slixmpp.
    Copied from https://github.com/Syndace/slixmpp-omemo/tree/main/examples
    """
    def __init__(self, *args: Any, **kwargs: Any) -> None:  # pylint: disable=redefined-outer-name
        super().__init__(*args, **kwargs)

        self.__storage: Storage
        #TODO: not sure why pconfig is not available through kwargs ?
        self.storage_dir: str = args[1]['storage']

    def plugin_init(self) -> None:
        self.__storage = StorageImpl(self.storage_dir)

        super().plugin_init()

    @property
    def storage(self) -> Storage:
        return self.__storage

    def setStorageDir(self, directory: str) -> None:
        self.storage_dir = directory

    @property
    def _btbv_enabled(self) -> bool:
        return True

    async def _devices_blindly_trusted(
        self,
        blindly_trusted: FrozenSet[DeviceInformation],
        identifier: Optional[str]
    ) -> None:
        log.info(f"[{identifier}] Devices trusted blindly: {blindly_trusted}")

    async def _prompt_manual_trust(
        self,
        manually_trusted: FrozenSet[DeviceInformation],
        identifier: Optional[str]
    ) -> None:
        """
        In case of manual trust, usually OMEMO use BTBV per default : https://gultsch.de/trust.html
        """
        session_mananger = await self.get_session_manager()

        for device in manually_trusted:
            while True:
                answer = input(f"[{identifier}] Trust the following device? (yes/no) {device}")
                if answer in { "yes", "no" }:
                    await session_mananger.set_trust(
                        device.bare_jid,
                        device.identity_key,
                        TrustLevel.TRUSTED.value if answer == "yes" else TrustLevel.DISTRUSTED.value
                    )
                    break
                print("Please answer yes or no.")

register_plugin(XEP_0384Impl)

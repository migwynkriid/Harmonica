import asyncio
import types
import pytest
import discord
from discord.ext import commands


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for pytest-asyncio."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def bot():
    """Provide a lightweight Bot instance for loading commands/extensions."""
    intents = discord.Intents.default()
    intents.message_content = True
    b = commands.Bot(command_prefix="!", intents=intents, help_command=None)
    yield b
    await b.close()


class StubAvatar:
    url = "http://example.com/avatar.png"


class StubRole:
    def __init__(self, name):
        self.name = name


class StubAuthor:
    def __init__(self, name="Tester", user_id=1):
        self.display_name = name
        self.display_avatar = StubAvatar()
        self.roles = []
        self.bot = False
        self.id = user_id


class StubChannel:
    def __init__(self, channel_id=123):
        self.id = channel_id


class StubGuild:
    def __init__(self):
        self.roles = [StubRole("DJ"), StubRole("Administrator")]
        self.name = "Test Guild"
        self.id = 1
        self.voice_client = None


class StubMessage:
    def __init__(self, embed=None):
        self.embed = embed
        self.channel = StubChannel()
        self.delete_called = False

    async def edit(self, embed=None, view=None):
        self.embed = embed

    async def delete(self):
        self.delete_called = True


class StubVoiceChannel:
    def __init__(self, name="VC", members=None):
        self.name = name
        self.members = members or []
        self.guild = StubGuild()
    async def connect(self, self_deaf=True):
        return StubVoiceClient(channel=self)


class StubVoiceState:
    def __init__(self, channel=None):
        self.channel = channel


class StubCtx:
    def __init__(self):
        self.author = StubAuthor()
        self.guild = StubGuild()
        self.prefix = "!"
        self.channel = StubChannel()
        self.voice_client = None
        self._sent = []
        self.id = 999

    async def send(self, embed=None, view=None, file=None):
        msg = StubMessage(embed)
        self._sent.append(msg)
        return msg


@pytest.fixture
def stub_ctx():
    """Provide a simple stub context for message tests."""
    return StubCtx()


@pytest.fixture
def stub_bot_instance():
    """Provide a simple bot_instance stub used by messages.update_or_send_message."""
    class StubBotInstance:
        def __init__(self):
            self.current_command_msg = None
            self.current_command_author = None
            self.queue = []
            self.queue_lock = asyncio.Lock()
            self.voice_client = None
            self.now_playing_message = None
            self.current_song = None
            self.queued_messages = {}
            self.waiting_for_song = False
            self.is_playing = False
            self.bot_loop = None
            
        async def cancel_downloads(self):
            return None

        async def update_activity(self):
            return None

    return StubBotInstance()


class StubVoiceClient:
    def __init__(self, channel=None):
        self._connected = True
        self._playing = False
        self.channel = channel or StubVoiceChannel()
        self.play_calls = []
        self.disconnect_called = False
        self.stop_called = False

    def is_connected(self):
        return self._connected

    def is_playing(self):
        return self._playing

    def play(self, source, after=None):
        self._playing = True
        self.play_calls.append((source, after))

    def stop(self):
        self._playing = False
        self.stop_called = True

    async def disconnect(self, force=True):
        self._connected = False
        self.disconnect_called = True
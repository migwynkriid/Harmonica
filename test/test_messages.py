import pytest
from scripts.messages import create_embed, update_or_send_message


def test_create_embed_basic(stub_ctx):
    embed = create_embed(
        "Test Title",
        "Test Description",
        color=0x3498db,
        thumbnail_url="http://example.com/tn.png",
        ctx=stub_ctx,
    )
    assert embed.title == "Test Title"
    assert "Test Description" in embed.description
    assert embed.timestamp is not None


@pytest.mark.asyncio
async def test_update_or_send_message_send_then_update(stub_ctx, stub_bot_instance):
    # First send
    embed1 = create_embed("First", "Message")
    msg1 = await update_or_send_message(stub_bot_instance, stub_ctx, embed1)
    assert msg1 is stub_ctx._sent[0]
    assert msg1.embed.title == "First"

    # Then update same message
    embed2 = create_embed("Second", "Updated")
    msg2 = await update_or_send_message(stub_bot_instance, stub_ctx, embed2)
    assert msg2 is msg1
    assert msg1.embed.title == "Second"
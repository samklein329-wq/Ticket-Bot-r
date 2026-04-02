import discord
import io
from datetime import timezone

async def generate_transcript(channel: discord.TextChannel) -> discord.File:
    """
    Fetches all messages in a ticket channel and returns a formatted .txt transcript as a discord.File.
    """
    lines = []
    lines.append("=" * 70)
    lines.append(f"  WAKESETTINGS — TICKET TRANSCRIPT")
    lines.append(f"  Channel : #{channel.name}  (ID: {channel.id})")
    lines.append(f"  Server  : {channel.guild.name}")
    lines.append("=" * 70)
    lines.append("")

    messages = []
    async for msg in channel.history(limit=2000, oldest_first=True):
        messages.append(msg)

    if not messages:
        lines.append("  [No messages found]")
    else:
        current_date = None
        for msg in messages:
            # Date separator
            msg_date = msg.created_at.astimezone(timezone.utc).strftime("%Y-%m-%d")
            if msg_date != current_date:
                current_date = msg_date
                lines.append("")
                lines.append(f"  ── {msg_date} ─────────────────────────────")
                lines.append("")

            timestamp = msg.created_at.astimezone(timezone.utc).strftime("%H:%M:%S UTC")
            author    = f"{msg.author} ({msg.author.id})"
            bot_tag   = " [BOT]" if msg.author.bot else ""

            # Header line
            lines.append(f"  [{timestamp}] {author}{bot_tag}")

            # Message content
            if msg.content:
                for line in msg.content.split("\n"):
                    lines.append(f"    {line}")

            # Embeds
            for embed in msg.embeds:
                lines.append(f"    [EMBED] {embed.title or '(no title)'}")
                if embed.description:
                    for dl in embed.description.split("\n"):
                        lines.append(f"      {dl}")
                for field in embed.fields:
                    lines.append(f"      • {field.name}: {field.value}")

            # Attachments
            for att in msg.attachments:
                lines.append(f"    [ATTACHMENT] {att.filename} — {att.url}")

            lines.append("")

    lines.append("")
    lines.append("=" * 70)
    lines.append(f"  Total messages: {len(messages)}")
    lines.append("=" * 70)

    content = "\n".join(lines)
    buffer  = io.BytesIO(content.encode("utf-8"))
    filename = f"transcript-{channel.name}.txt"
    return discord.File(buffer, filename=filename)

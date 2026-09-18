"""Generative UI: fixed blocks rendered from real tool output.

See blocks.py for the contract and why the model never authors a block.
"""

from app.agent.genui.blocks import Block, BlockName
from app.agent.genui.renderers import render_blocks

__all__ = ["Block", "BlockName", "render_blocks"]

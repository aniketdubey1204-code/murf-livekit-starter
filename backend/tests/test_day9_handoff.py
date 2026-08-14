import asyncio
import os
import sys
import logging

# Ensure backend directory is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_day9")

async def test_handoff():
    logger.info("=== Testing Day 9 Agent Handoff ===")

    from prompt import SYSTEM_PROMPT, RETURNS_SPECIALIST_PROMPT
    from agent import Assistant, ReturnsAgent

    logger.info("1. Instantiating Main Agent (Assistant)...")
    main_agent = Assistant(caller_id="test_user_123")
    assert main_agent.instructions is not None, "Main agent instructions missing!"
    logger.info("Main agent instantiated successfully.")

    logger.info("2. Testing transfer_to_returns_specialist tool on Main Agent...")
    # Mock RunContext
    class DummyContext:
        pass
    
    # Run the tool method
    transfer_res = await main_agent.transfer_to_returns_specialist(DummyContext())
    assert isinstance(transfer_res, tuple), "Tool output should be a tuple (Agent, message)"
    specialist_agent, message = transfer_res
    assert isinstance(specialist_agent, ReturnsAgent), f"Expected ReturnsAgent, got {type(specialist_agent)}"
    assert "रिटर्न और रिफंड विशेषज्ञ" in message or "स्पेशलिस्ट" in message or "कनेक्ट" in message, f"Unexpected message: {message}"
    logger.info(f"Handoff to specialist successful! Message: '{message}'")

    logger.info("3. Testing process_return_request tool on ReturnsAgent...")
    return_res = await specialist_agent.process_return_request(
        context=DummyContext(),
        item_name="Kachi Ghani Tel 1L",
        reason="Leakage / Damaged packaging",
        condition="damaged"
    )
    assert "RET-" in return_res, f"Expected return ID RET- in response, got: {return_res}"
    logger.info(f"Specialist return request processed successfully! Result: '{return_res}'")

    logger.info("4. Testing transfer_back_to_main_agent tool on ReturnsAgent...")
    transfer_back_res = await specialist_agent.transfer_back_to_main_agent(DummyContext())
    assert isinstance(transfer_back_res, tuple), "Tool output should be a tuple (Agent, message)"
    returned_main_agent, back_message = transfer_back_res
    assert isinstance(returned_main_agent, Assistant), f"Expected Assistant, got {type(returned_main_agent)}"
    logger.info(f"Handoff back to main agent successful! Message: '{back_message}'")

    logger.info("=== ALL DAY 9 HANDOFF TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(test_handoff())

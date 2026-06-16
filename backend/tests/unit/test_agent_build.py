from app.agent.agent import build_agent


def test_build_agent_exposes_search_tool_and_model():
    agent = build_agent(model="gpt-5-mini")
    assert agent.model == "gpt-5-mini"
    assert "search_archive" in [tool.name for tool in agent.tools]

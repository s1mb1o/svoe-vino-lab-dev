from chto_za_vino_bot.host_demo import run_demo


async def test_host_demo_runs_the_pipeline_without_private_services():
    result = await run_demo()

    assert result["demo"] == "self-contained"
    assert result["moderation"] == {"performed": True, "safe": True}
    assert result["quality"] == {"acceptable": True, "issues": []}
    assert result["recognition"]["confident"] is True
    assert result["recognition"]["pipeline"] == "host-demo"
    assert result["recognition"]["page_url"].startswith("https://vino-svoe.ru/")

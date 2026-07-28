# """
# server.py — Repair Vs Replacement Agent
# ───────────────────────────────────────
# LangGraph agent that compares repair vs. replacement costs for
# a damaged item and recommends a course of action.

# Port: 8912
# MCP : http://localhost:8900/api/v1/repair_vs_replacement/mcp

# Run:
#     py -3 server.py
# """

# import json
# import logging
# import os
# import sys
# import time
# import traceback
# from datetime import datetime, timedelta
# from typing import Annotated, TypedDict

# import uvicorn
# from dotenv import load_dotenv, find_dotenv
# from fastapi import FastAPI, Request
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import StreamingResponse
# from langchain_core.messages import AIMessage, SystemMessage
# from langchain_mcp_adapters.client import MultiServerMCPClient
# from langchain_openai.chat_models import AzureChatOpenAI
# from langgraph.graph import END, START, StateGraph
# from langgraph.graph.message import add_messages
# from langgraph.prebuilt import ToolNode

# load_dotenv(find_dotenv())

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
#     stream=sys.stdout,
#     force=True,
# )
# logger = logging.getLogger("repair_vs_replacement_agent")

# PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY", "")
# PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "")
# MCP_URL = os.getenv("MCP_URL", "http://localhost:8900/api/v1/repair_vs_replacement/mcp")
# AGENT_PORT = int(os.getenv("AGENT_PORT", "8912"))

# config_mcp_server = {
#     "repair_vs_replacement_mcp": {
#         "url": MCP_URL,
#         "transport": "streamable_http",
#         "timeout": timedelta(seconds=120),
#         "sse_read_timeout": timedelta(seconds=600),
#     }
# }

# app = FastAPI(title="Repair Vs Replacement Agent")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# class State(TypedDict):
#     messages: Annotated[list, add_messages]


# def router(state: State):
#     last = state["messages"][-1]
#     if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
#         return "tools"
#     if isinstance(last, AIMessage) and last.content:
#         if "Continue" in last.content:
#             return "tools"
#         if "End" in last.content:
#             return "End"
#     return "End"


# _FALLBACK_PROMPT = """
# You are the Repair vs Replacement Agent for an insurance claims platform,
# assisting a Claims Adjuster.

# Given a claim_id, item_type, item_age, and useful_life_remaining, your
# workflow is:

# 1. Call compare_repair_vs_replace with these inputs. This will look up or
#    estimate repair and replacement costs, apply the rule: if
#    repair_cost > 0.6 * replacement_cost OR item_age >= useful_life_remaining
#    then recommend "Replace", else "Repair", and store the result.
# 2. Explain to the adjuster the recommendation, the repair vs replacement
#    cost comparison, and the confidence score.

# When you have completed the task, end your response with "End".
# """


# def load_prompt() -> str:
#     if not PHOENIX_ENDPOINT:
#         raise RuntimeError("Phoenix not configured")
#     from phoenix.client import Client
#     client = Client(base_url=PHOENIX_ENDPOINT, api_key=PHOENIX_API_KEY)
#     prompt = client.prompts.get(name="repair_vs_replacement_agent", label="production")
#     prompt_set = prompt._template["messages"]
#     system_msg = next(
#         (item["content"][0]["text"] for item in prompt_set if item.get("role") == "system"),
#         None,
#     )
#     if not system_msg:
#         raise ValueError("System prompt is empty or missing in Phoenix")
#     return system_msg


# def create_graph(model, tools, prompt):
#     graph_builder = StateGraph(State)
#     llm_with_tools = model.bind_tools(tools)

#     async def agent_node(state: State):
#         messages = state["messages"]
#         all_messages = [SystemMessage(content=prompt)] + messages
#         message = await llm_with_tools.ainvoke(all_messages)
#         return {"messages": [message]}

#     graph_builder.add_node("agent", agent_node)
#     graph_builder.add_node("tools", ToolNode(tools=tools))
#     graph_builder.add_edge(START, "agent")
#     graph_builder.add_conditional_edges("agent", router, {"tools": "tools", "End": END})
#     graph_builder.add_edge("tools", "agent")
#     return graph_builder.compile()


# async def get_tools():
#     client = MultiServerMCPClient(config_mcp_server)
#     tools = await client.get_tools()
#     logger.info("Tools loaded from MCP: %s", [t.name for t in tools])
#     return tools


# async def stream_graph(graph, initial_state, config):
#     async for event in graph.astream_events(initial_state, config=config, version="v2"):
#         kind = event.get("event", "")

#         if kind == "on_chat_model_stream":
#             chunk = event["data"].get("chunk")
#             if chunk and hasattr(chunk, "content") and chunk.content:
#                 yield f"data: {chunk.content}\n\n"

#         elif kind == "on_tool_start":
#             tool_name = event.get("name", "unknown_tool")
#             yield f"data: [Tool: {tool_name}] Starting...\n\n"

#         elif kind == "on_tool_end":
#             tool_name = event.get("name", "unknown_tool")
#             yield f"data: [Tool: {tool_name}] Done\n\n"


# @app.post("/chat")
# async def chat_stream(request: Request):
#     load_dotenv(find_dotenv())

#     tools = await get_tools()

#     model = AzureChatOpenAI(
#         api_key=os.getenv("AZURE_OPENAI_API_KEY"),
#         api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
#         azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
#         azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
#     )

#     try:
#         system_prompt = load_prompt()
#     except Exception as e:
#         logger.warning("Phoenix prompt load failed (%s) — using fallback prompt", e)
#         system_prompt = _FALLBACK_PROMPT

#     body = await request.json()
#     user_message = body.get("message", "Recommend repair vs replacement for this item")

#     graph = create_graph(model=model, tools=tools, prompt=system_prompt)

#     async def generate():
#         start = time.time()
#         last_event_at = start
#         last_tool = None
#         try:
#             async for event in stream_graph(
#                 graph=graph,
#                 initial_state={"messages": [user_message]},
#                 config={"recursion_limit": 250},
#             ):
#                 last_event_at = time.time()
#                 if isinstance(event, str) and event.startswith("data: [Tool:"):
#                     try:
#                         last_tool = event.split("[Tool:", 1)[1].split("]", 1)[0]
#                     except Exception:
#                         pass
#                 yield event
#         except BaseException as e:
#             elapsed = time.time() - start
#             since_last = time.time() - last_event_at
#             err = {
#                 "exception_class": type(e).__name__,
#                 "message": str(e),
#                 "elapsed_total_seconds": round(elapsed, 2),
#                 "seconds_since_last_event": round(since_last, 2),
#                 "last_tool_invoked": last_tool,
#                 "traceback": traceback.format_exc(),
#                 "timestamp_utc": datetime.utcnow().isoformat(),
#             }
#             logger.error("AGENT_ERROR %s", json.dumps(err, default=str))
#             try:
#                 yield f"data: [AGENT_ERROR] {json.dumps(err, default=str)}\n\n"
#             except Exception:
#                 pass
#             import asyncio
#             if isinstance(e, asyncio.CancelledError):
#                 raise

#     return StreamingResponse(generate(), media_type="text/event-stream")


# @app.get("/health")
# async def health():
#     return {"status": "healthy", "agent": "repair_vs_replacement_agent"}


# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)









"""
server.py — Repair Vs Replacement Agent
───────────────────────────────────────
LangGraph agent that compares repair vs. replacement costs for
a damaged item and recommends a course of action.

Port: 8912
MCP : http://localhost:8900/api/v1/repair_vs_replacement/mcp

Run:
    py -3 server.py
"""

import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timedelta
from typing import Annotated, TypedDict

import uvicorn
from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai.chat_models import AzureChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

load_dotenv(find_dotenv())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger("repair_vs_replacement_agent")

PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY", "")
PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "")
MCP_URL = os.getenv("MCP_URL", "http://localhost:5800/api/v1/repair_vs_replacement/mcp")
# MCP_URL =  "http://localhost:5900/api/v1/repair_vs_replacement/mcp"

AGENT_PORT = int(os.getenv("AGENT_PORT", "8912"))

# AGENT_PORT = "8912"

config_mcp_server = {
    "repair_vs_replacement_mcp": {
        "url": MCP_URL,
        "transport": "streamable_http",
        "timeout": timedelta(seconds=120),
        "sse_read_timeout": timedelta(seconds=600),
    }
}

app = FastAPI(title="Repair Vs Replacement Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class State(TypedDict):
    messages: Annotated[list, add_messages]


def router(state: State):
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"
    if isinstance(last, AIMessage) and last.content:
        if "Continue" in last.content:
            return "tools"
        if "End" in last.content:
            return "End"
    return "End"


# _FALLBACK_PROMPT = """
# You are the Repair vs Replacement Agent for an insurance claims platform,
# assisting a Claims Adjuster.

# Given a claim_number, item_type, item_age, and useful_life_remaining, your
# workflow is:

# 1. Look up the internal claim_id from the claims table.
# 2. Retrieve any repair_costs and replacement_costs for that claim_id.
# 3. Call compare_repair_vs_replace with these inputs. This will look up or
#    estimate repair and replacement costs, apply the rule: if
#    repair_cost > 0.6 * replacement_cost OR item_age >= useful_life_remaining
#    then recommend "Replace", else "Repair", and store the result.
# 4. Explain to the adjuster the recommendation, the repair vs replacement
#    cost comparison, and the confidence score.

# When you have completed the task, end your response with "End".
# """


# _FALLBACK_PROMPT = """
# You are the Repair vs Replacement Agent for an insurance claims platform assisting a Claims Adjuster.
# Given a claim_number, item_age and useful_life_remaining, execute the following workflow:
# 1. Look up the internal claim_id from the claims table.
# If the claim does not exist, immediately inform the adjuster that the claim number is invalid and stop.
# Do not call any other tools.
# 2. Retrieve the damage item.
# If no damage item exists, inform the adjuster that Damage Assessment has not yet been completed.
# Stop immediately.
# Do not call any additional tools.
# 3. Check whether repair_costs and replacement_costs already exist for the claim and item.
# 4. If both records exist, use the stored repair and replacement estimates.
# 5. If either record is missing, estimate realistic repair and replacement costs using available claim information, then write the generated repair estimate to the repair_costs table and the generated replacement estimate to the replacement_costs table.
# 6. Compare the repair and replacement costs using the business rule:
#   - If repair_cost > 60% of replacement_cost, or
#   - item_age >= useful_life_remaining,
#   recommend "Replace"; otherwise recommend "Repair".
# 7. Store the final recommendation, confidence score and comparison results in the estimates table.
# 8. Explain to the adjuster why the recommendation was made, including the repair cost, replacement cost and confidence score.
# When the workflow is complete, end your response with "End".
# 9. After explaining the recommendation, call the tool
# write_repair_vs_replacement_decision
# to store the AI recommendation.
# 10. Then ask the Claims Adjuster:
# Please confirm your final decision by replying:
# For claim <claim_number>, Repair.
# or
# For claim <claim_number>, Replace.
# 11. When the adjuster replies, call the tool
# update_repair_vs_replacement_decision
# using the supplied claim_number and decision.
# 12. Confirm that the adjuster's decision has been recorded successfully.
# 13. End the conversation with "End".

# """
















# _FALLBACK_PROMPT = """
# You are the Repair vs Replacement Agent for an insurance claims platform assisting a Claims Adjuster.

# Your responsibility is to evaluate whether a damaged item should be repaired or replaced, explain your recommendation, record the AI recommendation, and then record the Claims Adjuster's final decision.

# Follow this workflow exactly.

# 1. Look up the internal claim_id from the claims table.

# If the claim does not exist:
# - Inform the Claims Adjuster that the claim number is invalid.
# - Stop immediately.
# - Do not call any additional tools.

# 2. Retrieve the damage item for the claim.

# If no damage item exists:
# - Inform the Claims Adjuster that Damage Assessment has not yet been completed.
# - Stop immediately.
# - Do not call any additional tools.

# 3. Call the tool:

# compare_repair_vs_replace

# using the supplied claim_number, item_age and useful_life_remaining.

# This tool is responsible for:
# - Reading existing repair_costs and replacement_costs if they already exist.
# - Generating repair and replacement estimates if they do not exist.
# - Writing repair_costs.
# - Writing replacement_costs.
# - Writing estimates.
# - Calculating the recommendation.
# - Returning the repair cost, replacement cost, recommendation and confidence score.

# Do not attempt to calculate repair or replacement costs yourself.

# 4. Explain the recommendation to the Claims Adjuster.

# Your explanation should include:
# - Repair Cost
# - Replacement Cost
# - Recommended Action (Repair or Replace)
# - Confidence Score
# - A concise explanation of why the recommendation was made.

# 5. Immediately after explaining the recommendation, call the tool:

# write_repair_vs_replacement_decision

# using:
# - claim_number
# - recommended_action
# - ai_generated_message

# The ai_generated_message should contain the recommendation that was explained to the Claims Adjuster.

# This tool records the AI recommendation in the repair_vs_replacement_decisions table.

# If the tool reports that the recommendation already exists, continue the workflow normally.

# 6. Ask the Claims Adjuster to confirm the final decision.

# Use the following wording:

# Please confirm your final decision.

# Reply using one of the following formats:

# For claim <claim_number>, Repair.

# or

# For claim <claim_number>, Replace.

# Do not assume the Claims Adjuster's decision.

# Wait for the user's reply.

# 7. When the Claims Adjuster replies with either Repair or Replace, call the tool:

# update_repair_vs_replacement_decision

# using:
# - claim_number
# - decision

# This tool updates the previously created recommendation record with the Claims Adjuster's final decision.

# 8. After the update tool completes successfully, confirm the decision has been recorded.

# For example:

# "The Claims Adjuster's decision has been successfully recorded."

# 9. End the conversation by responding with:

# End

# Important Rules

# - Never call update_repair_vs_replacement_decision before write_repair_vs_replacement_decision.
# - Never call write_repair_vs_replacement_decision before compare_repair_vs_replace has completed successfully.
# - Never calculate repair or replacement costs yourself.
# - Always use compare_repair_vs_replace to obtain the recommendation.
# - Always wait for the Claims Adjuster's confirmation before updating the final decision.
# - Never skip any step in the workflow.
# """














_FALLBACK_PROMPT = """
You are the Repair vs Replacement Agent for an insurance claims platform assisting a Claims Adjuster.

You have access to the following tools:

• compare_repair_vs_replace
• write_repair_vs_replacement_decision
• update_repair_vs_replacement_decision

Always use tools whenever appropriate. Never fabricate repair costs, replacement costs, recommendations, or database status.

====================================================
IMPORTANT
====================================================

There are TWO different workflows.

----------------------------------------------------
WORKFLOW 1 — Generate a Recommendation
----------------------------------------------------

Use this workflow when the user asks questions such as:

- Should this item be repaired or replaced?
- Recommend repair vs replacement.
- Compare repair and replacement.
- Evaluate claim <claim_number>.

Steps:

1. Extract:
   - claim_number
   - item_age
   - useful_life_remaining

2. Call:

compare_repair_vs_replace

using those values.

3. The tool returns:
   - repair_cost
   - replacement_cost
   - recommendation
   - confidence_score
   - estimate

Use ONLY those returned values.

Do not recalculate anything yourself.

4. Explain to the adjuster:

- Repair Cost
- Replacement Cost
- Recommended Action
- Confidence Score
- Why the recommendation was made

5. After explaining the recommendation, immediately call:

write_repair_vs_replacement_decision

using:

- claim_number
- recommended_action
- ai_generated_message

The ai_generated_message should contain a concise summary of the recommendation.

6. If the tool succeeds, ask the Claims Adjuster for confirmation exactly like this:

Please confirm your final decision.

Reply using one of the following formats:

For claim <claim_number>, Repair.

or

For claim <claim_number>, Replace.

Do NOT call compare_repair_vs_replace again after asking for confirmation.

Wait for the user's reply.

----------------------------------------------------
WORKFLOW 2 — Record the Adjuster's Final Decision
----------------------------------------------------

If the user's message is ONLY a confirmation such as:

For claim CLM-2026-1101, Repair.

or

For claim CLM-2026-1101, Replace.

DO NOT call compare_repair_vs_replace.

DO NOT generate another recommendation.

DO NOT calculate costs again.

DO NOT ask for confirmation again.

Instead:

1. Extract:
   - claim_number
   - decision

2. Immediately call:

update_repair_vs_replacement_decision

using those values.

3. If successful, reply:

The adjuster's decision has been recorded successfully.

Claim Number: <claim_number>

Final Decision: <decision>

End

====================================================
Failure Handling
====================================================

If compare_repair_vs_replace reports:

- claim not found

Inform the user that the claim number is invalid.

Stop.

Do not call any other tools.

----------------------------------------------------

If damage assessment is unavailable:

Inform the user that Damage Assessment has not yet been completed.

Stop.

Do not call any other tools.

----------------------------------------------------

If write_repair_vs_replacement_decision fails:

Inform the user that the recommendation was generated successfully but could not be stored because of a system error.

Do NOT ask the user to confirm until the recommendation has been stored successfully.

End.

----------------------------------------------------

If update_repair_vs_replacement_decision fails:

Inform the user that the recommendation exists but the final decision could not be recorded because of a system error.

End.

====================================================
General Rules
====================================================

• Never invent repair costs.
• Never invent replacement costs.
• Never invent confidence scores.
• Always use tool outputs.
• Never call compare_repair_vs_replace more than once for the same recommendation request.
• Never call write_repair_vs_replacement_decision before compare_repair_vs_replace.
• Never call update_repair_vs_replacement_decision until the user explicitly confirms Repair or Replace.
• Once the adjuster's decision has been recorded successfully, end the conversation by replying with:

End

"""

def load_prompt() -> str:
    if not PHOENIX_ENDPOINT:
        raise RuntimeError("Phoenix not configured")
    from phoenix.client import Client
    client = Client(base_url=PHOENIX_ENDPOINT, api_key=PHOENIX_API_KEY)
    prompt = client.prompts.get(name="repair_vs_replacement_agent", label="production")
    prompt_set = prompt._template["messages"]
    system_msg = next(
        (item["content"][0]["text"] for item in prompt_set if item.get("role") == "system"),
        None,
    )
    if not system_msg:
        raise ValueError("System prompt is empty or missing in Phoenix")
    return system_msg


def create_graph(model, tools, prompt):
    graph_builder = StateGraph(State)
    llm_with_tools = model.bind_tools(tools)

    # async def agent_node(state: State):
    #     messages = state["messages"]
    #     all_messages = [SystemMessage(content=prompt)] + messages
    #     message = await llm_with_tools.ainvoke(all_messages)
    #     return {"messages": [message]}

    async def agent_node(state: State):
        messages = state["messages"]
        all_messages = [SystemMessage(content=prompt)] + messages
        message = await llm_with_tools.ainvoke(all_messages)
        logger.info("AI MESSAGE = %s", message)
        logger.info("TOOL CALLS = %s", getattr(message, "tool_calls", None))
        return {"messages": [message]}

    graph_builder.add_node("agent", agent_node)
    graph_builder.add_node("tools", ToolNode(tools=tools))
    graph_builder.add_edge(START, "agent")
    graph_builder.add_conditional_edges("agent", router, {"tools": "tools", "End": END})
    graph_builder.add_edge("tools", "agent")
    return graph_builder.compile()


async def get_tools():
    client = MultiServerMCPClient(config_mcp_server)
    tools = await client.get_tools()
    logger.info("Tools loaded from MCP: %s", [t.name for t in tools])
    return tools


async def stream_graph(graph, initial_state, config):
    async for event in graph.astream_events(initial_state, config=config, version="v2"):
        kind = event.get("event", "")

        if kind == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                yield f"data: {chunk.content}\n\n"

        elif kind == "on_tool_start":
            tool_name = event.get("name", "unknown_tool")
            yield f"data: [Tool: {tool_name}] Starting...\n\n"

        elif kind == "on_tool_end":
            tool_name = event.get("name", "unknown_tool")
            yield f"data: [Tool: {tool_name}] Done\n\n"


@app.post("/chat")
async def chat_stream(request: Request):
    load_dotenv(find_dotenv())

    tools = await get_tools()

    model = AzureChatOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )

    try:
        system_prompt = load_prompt()
    except Exception as e:
        logger.warning("Phoenix prompt load failed (%s) — using fallback prompt", e)
        system_prompt = _FALLBACK_PROMPT

    body = await request.json()
    user_message = body.get("message", "Recommend repair vs replacement for this item")

    graph = create_graph(model=model, tools=tools, prompt=system_prompt)

    async def generate():
        start = time.time()
        last_event_at = start
        last_tool = None
        try:
            async for event in stream_graph(
                graph=graph,
                initial_state={"messages": [user_message]},
                config={"recursion_limit": 250},
            ):
                last_event_at = time.time()
                if isinstance(event, str) and event.startswith("data: [Tool:"):
                    try:
                        last_tool = event.split("[Tool:", 1)[1].split("]", 1)[0]
                    except Exception:
                        pass
                yield event
        except BaseException as e:
            elapsed = time.time() - start
            since_last = time.time() - last_event_at
            err = {
                "exception_class": type(e).__name__,
                "message": str(e),
                "elapsed_total_seconds": round(elapsed, 2),
                "seconds_since_last_event": round(since_last, 2),
                "last_tool_invoked": last_tool,
                "traceback": traceback.format_exc(),
                "timestamp_utc": datetime.utcnow().isoformat(),
            }
            logger.error("AGENT_ERROR %s", json.dumps(err, default=str))
            try:
                yield f"data: [AGENT_ERROR] {json.dumps(err, default=str)}\n\n"
            except Exception:
                pass
            import asyncio
            if isinstance(e, asyncio.CancelledError):
                raise

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "repair_vs_replacement_agent"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)

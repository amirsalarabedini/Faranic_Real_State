from openai import OpenAI
import os
import json
from datetime import datetime
from agents import Agent, FileSearchTool, Runner, WebSearchTool, function_tool
import asyncio

# client = OpenAI()

# user_query = "What is the book about?"

# results = client.vector_stores.search(
#     vector_store_id="vs_687521bfdcf88191a98e649dbb56eb81",
#     query=user_query,
# )

# # Save results to a file
# output_data = {
#     "timestamp": datetime.now().isoformat(),
#     "query": user_query,
#     "results": results.model_dump() if hasattr(results, 'model_dump') else str(results)
# }

# with open("search_results.json", "w", encoding="utf-8") as f:
#     json.dump(output_data, f, indent=2, ensure_ascii=False)

# print(f"Results saved to search_results.json")
# print(f"Query: {user_query}")
# print(f"Results: {results}")

retrieval_agent = Agent(
    name="RetrievalAgent",
    instructions=(
        """
        You are a housing market analysis expert with access to a comprehensive knowledge base about Iranian housing market investment strategies. Your primary role is to extract and apply analytical methods from the book to solve user problems.
        You are an expert at extracting analytical methods, frameworks, and problem-solving approaches from housing market literature.
        
        Your job is to:
        1. Search the knowledge base for specific analytical methods, frameworks, and step-by-step processes
        2. Identify quantitative and qualitative analysis approaches
        3. Extract decision-making criteria and evaluation methods
        4. Find comparative analysis techniques
        5. Locate risk assessment frameworks
        
        Focus on finding "HOW TO" content rather than just facts:
        - Investment analysis methods
        - Market evaluation frameworks  
        - Comparative analysis techniques
        - Risk assessment processes
        - Decision-making criteria
        - Performance measurement methods
        
        Return your findings in this format:
        **METHOD FOUND:** [Name of method/framework]
        **DESCRIPTION:** [How it works]
        **APPLICATION:** [When to use it]
        **STEPS:** [Step-by-step process if available]
        **CRITERIA:** [Success metrics or evaluation criteria]

        Remember: You are not just providing information - you are applying the book's analytical methods to solve problems.
        """
    ),
    tools=[
        FileSearchTool(
            max_num_results=8,  # Increased for better method extraction
            vector_store_ids=["vs_687521bfdcf88191a98e649dbb56eb81"],
            include_search_results=True,
        )
    ],
    model="o4-mini",
)



async def main() -> None:
    query = "برای مقابسه قیمت در منطقه ۲۲ با ۱۳ تهران چی کار باید بکنم؟"
    result = await Runner.run(retrieval_agent, query)
    print("\n===== FINAL ANSWER =====\n")
    print(result.final_output)
    #save result to file
    with open("result.md", "w", encoding="utf-8") as f:
        f.write(str(result.final_output))

if __name__ == "__main__":
    asyncio.run(main())
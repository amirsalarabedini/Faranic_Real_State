from agents import Agent, FileSearchTool, Runner, function_tool
import asyncio
from typing import List

# Strategic search patterns specifically designed to find analytical methods
ANALYTICAL_SEARCH_PATTERNS = {
    "methods": [
        "روش تحلیل",  # Analysis method
        "چگونه تحلیل",  # How to analyze
        "مراحل بررسی",  # Investigation steps
        "فرآیند ارزیابی",  # Evaluation process
        "معیارهای سنجش",  # Assessment criteria
    ],
    "frameworks": [
        "چارچوب تحلیل",  # Analysis framework
        "مدل ارزیابی",  # Evaluation model
        "سیستم تصمیم گیری",  # Decision-making system
        "الگوی بررسی",  # Investigation pattern
    ],
    "comparison": [
        "مقایسه منطقه",  # Region comparison
        "مقایسه قیمت",  # Price comparison
        "مقایسه سرمایه گذاری",  # Investment comparison
        "بررسی تطبیقی",  # Comparative analysis
    ],
    "risk_assessment": [
        "ارزیابی ریسک",  # Risk assessment
        "عوامل ریسک",  # Risk factors
        "کاهش ریسک",  # Risk mitigation
        "مدیریت ریسک",  # Risk management
    ],
    "decision_criteria": [
        "معیارهای تصمیم",  # Decision criteria
        "شاخص های ارزیابی",  # Evaluation indicators
        "معیارهای انتخاب",  # Selection criteria
        "فاکتورهای کلیدی",  # Key factors
    ],
    "timing": [
        "زمان بندی سرمایه گذاری",  # Investment timing
        "چرخه بازار",  # Market cycle
        "زمان مناسب خرید",  # Best time to buy
        "سیکل قیمت",  # Price cycle
    ]
}

def generate_search_queries(user_query: str) -> List[str]:
    """Generate strategic search queries based on the user's question."""
    queries = []
    
    # Direct queries
    queries.extend([
        f"چگونه {user_query}",  # How to [user_query]
        f"روش {user_query}",  # Method for [user_query]
        f"تحلیل {user_query}",  # Analysis of [user_query]
        f"معیارهای {user_query}",  # Criteria for [user_query]
        f"فرآیند {user_query}",  # Process for [user_query]
    ])
    
    # Category-based queries
    for category, patterns in ANALYTICAL_SEARCH_PATTERNS.items():
        for pattern in patterns:
            queries.append(f"{pattern} {user_query}")
    
    # Specific method-finding queries
    queries.extend([
        "مراحل تحلیل بازار مسکن",  # Housing market analysis steps
        "روش ارزیابی سرمایه گذاری املاک",  # Real estate investment evaluation method
        "چارچوب تصمیم گیری املاک",  # Real estate decision framework
        "معیارهای انتخاب منطقه",  # Area selection criteria
        "فاکتورهای مؤثر در قیمت",  # Price-affecting factors
        "روش مقایسه مناطق",  # Area comparison method
    ])
    
    return queries

@function_tool
async def strategic_method_search(user_query: str) -> str:
    """Perform strategic searches to find analytical methods from the book."""
    search_queries = generate_search_queries(user_query)
    
    # Create agent for method searching
    method_search_agent = Agent(
        name="MethodSearchAgent",
        instructions=(
            """
            You are searching for analytical methods, frameworks, and step-by-step processes from a housing market analysis book.
            
            Extract:
            1. Specific methods and frameworks mentioned
            2. Step-by-step processes and procedures
            3. Evaluation criteria and benchmarks
            4. Decision-making frameworks
            5. Risk assessment approaches
            6. Comparative analysis techniques
            
            Focus on actionable "how-to" content rather than just facts.
            If you find a method, explain:
            - What it is
            - How it works
            - When to use it
            - Steps to implement it
            """
        ),
        tools=[
            FileSearchTool(
                max_num_results=5,
                vector_store_ids=["vs_687521bfdcf88191a98e649dbb56eb81"],
                include_search_results=True,
            )
        ],
        model="o4-mini",
    )
    
    # Run searches in parallel for efficiency
    search_results = []
    batch_size = 5  # Process in batches to avoid overwhelming the system
    
    for i in range(0, len(search_queries), batch_size):
        batch = search_queries[i:i + batch_size]
        tasks = [Runner.run(method_search_agent, query) for query in batch]
        batch_results = await asyncio.gather(*tasks)
        search_results.extend([str(result.final_output) for result in batch_results])
    
    # Combine and deduplicate results
    combined_results = "\n\n" + "="*50 + "\n\n".join(search_results)
    return combined_results

# Enhanced agent that uses strategic search
enhanced_strategic_agent = Agent(
    name="EnhancedStrategicAgent",
    instructions=(
        """
        You are an advanced housing market analysis expert that systematically extracts and applies analytical methods from the book.
        
        Process:
        1. Use strategic_method_search to find relevant analytical methods
        2. Extract the most applicable methods for the user's question
        3. Apply these methods step-by-step to solve the problem
        4. Provide structured analysis following the book's approaches
        
        Structure your response with these sections:
        
        ## **executive_summary (The Core Answer)**
        - Direct answer using the book's analytical method
        - Reference the specific framework applied
        - State the recommended approach
        
        ## **market_principles (The Analytical Framework)**
        - Explain the method from the book
        - Show how it applies to this question
        - Include relevant factors (supply/demand, internal/external factors)
        - Reference quantitative/qualitative aspects
        
        ## **recommended_strategies (Step-by-Step Application)**
        - Break down the method into actionable steps
        - Apply each step to the specific situation
        - Provide measurable criteria and benchmarks
        - Include implementation timeline
        
        ## **risks_and_mitigation (Analysis Validation)**
        - Identify method limitations
        - Mention alternative approaches from the book
        - Provide risk mitigation strategies
        - Include scenario considerations
        
        Always prioritize extracting and applying the book's specific methods rather than providing general advice.
        """
    ),
    tools=[
        strategic_method_search,
        FileSearchTool(
            max_num_results=8,
            vector_store_ids=["vs_687521bfdcf88191a98e649dbb56eb81"],
            include_search_results=True,
        )
    ],
    model="o4-mini",
)

# Usage function
async def analyze_with_strategic_agent(user_query: str) -> str:
    """Analyze using the strategic search agent."""
    result = await Runner.run(enhanced_strategic_agent, user_query)
    return str(result.final_output)

# Test function
async def main():
    """Test the strategic search agent."""
    test_query = "برای مقایسه قیمت در منطقه ۲۲ با ۱۳ تهران چه کار باید بکنم؟"
    
    print("Testing Strategic Search Agent...")
    print(f"Query: {test_query}")
    print("="*50)
    
    result = await analyze_with_strategic_agent(test_query)
    print(result)
    
    # Save result
    with open("strategic_analysis_result.md", "w", encoding="utf-8") as f:
        f.write(f"# Strategic Analysis\n\n**Query:** {test_query}\n\n{result}")

if __name__ == "__main__":
    asyncio.run(main()) 
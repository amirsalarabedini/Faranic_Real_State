from agents import Agent, FileSearchTool, Runner, function_tool
import asyncio
from typing import List, Dict, Any

# Method Extraction Agent - Finds analytical frameworks in the book
method_extractor = Agent(
    name="MethodExtractor",
    instructions=(
        """
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
        """
    ),
    tools=[
        FileSearchTool(
            max_num_results=10,
            vector_store_ids=["vs_687521bfdcf88191a98e649dbb56eb81"],
            include_search_results=True,
        )
    ],
    model="o4-mini",
)

# Method Application Agent - Applies extracted methods to specific problems
method_applier = Agent(
    name="MethodApplier",
    instructions=(
        """
        You are an expert at applying analytical methods to solve specific housing market problems.
        
        Given:
        1. A user's specific question/problem
        2. Relevant analytical methods from the book
        3. Context about the situation
        
        Your job is to:
        1. Select the most appropriate analytical method for the problem
        2. Adapt the method to the specific situation
        3. Apply it step-by-step to generate actionable insights
        4. Provide concrete recommendations based on the analysis
        
        Structure your response as:
        **SELECTED METHOD:** [Which method you're applying]
        **ADAPTATION:** [How you've adapted it to this specific case]
        **STEP-BY-STEP APPLICATION:**
        - Step 1: [Action and rationale]
        - Step 2: [Action and rationale]
        - ...
        **ANALYSIS RESULTS:** [What the method reveals]
        **RECOMMENDATIONS:** [Specific actionable steps]
        """
    ),
    model="o4-mini",
)

# Synthesis Agent - Combines everything into final structured response
synthesis_agent = Agent(
    name="SynthesisAgent",
    instructions=(
        """
        You are an expert at synthesizing analytical findings into comprehensive, actionable responses.
        
        Given method extraction results and application results, create a final response with exactly these sections:
        
        ## **executive_summary (The Core Answer)**
        - Direct analytical conclusion using the book's method
        - Reference the specific framework applied
        - State the recommended approach clearly
        
        ## **market_principles (The Analytical Framework)**
        - Explain the analytical method used from the book
        - Show how it applies to this specific question
        - Include relevant factors (supply/demand, internal/external, etc.)
        - Reference quantitative/qualitative aspects
        
        ## **recommended_strategies (Step-by-Step Application)**
        - Break down the method into actionable steps
        - Apply each step to the specific situation
        - Provide measurable criteria and benchmarks
        - Include timeline and implementation guidance
        
        ## **risks_and_mitigation (Analysis Validation)**
        - Identify method limitations
        - Mention alternative approaches from the book
        - Provide risk mitigation strategies
        - Include scenario considerations
        
        Ensure the response is practical, actionable, and directly applies the book's analytical methods.
        """
    ),
    model="o4-mini",
)

# Function tools to connect the agents
@function_tool
async def extract_methods(query: str) -> str:
    """Extract relevant analytical methods from the book for the given query."""
    # Search for methods with different keywords
    method_queries = [
        f"How to analyze {query}",
        f"Method for evaluating {query}",
        f"Framework for {query}",
        f"Steps to assess {query}",
        f"Criteria for {query}",
        f"Approach to {query}"
    ]
    
    results = []
    for method_query in method_queries:
        result = await Runner.run(method_extractor, method_query)
        results.append(str(result.final_output))
    
    return "\n\n---\n\n".join(results)

@function_tool
async def apply_methods(query: str, methods: str) -> str:
    """Apply the extracted methods to solve the specific problem."""
    application_prompt = f"""
    USER PROBLEM: {query}
    
    AVAILABLE METHODS: {methods}
    
    Apply the most appropriate method(s) to solve this specific problem.
    """
    
    result = await Runner.run(method_applier, application_prompt)
    return str(result.final_output)

# Main Enhanced Agent
enhanced_analytical_agent = Agent(
    name="EnhancedAnalyticalAgent",
    instructions=(
        """
        You are an advanced housing market analysis expert that uses a systematic approach to extract and apply analytical methods from the knowledge base.
        
        For each user question:
        1. First, use extract_methods to find relevant analytical frameworks from the book
        2. Then, use apply_methods to apply those frameworks to the specific problem
        3. Finally, synthesize everything into a comprehensive response
        
        Always ensure you're applying the book's proven methods rather than just providing general information.
        """
    ),
    tools=[
        extract_methods,
        apply_methods,
        FileSearchTool(
            max_num_results=8,
            vector_store_ids=["vs_687521bfdcf88191a98e649dbb56eb81"],
            include_search_results=True,
        )
    ],
    model="o4-mini",
)

# Usage example
async def analyze_with_enhanced_agent(user_query: str) -> str:
    """
    Use the enhanced analytical agent to solve problems using book methods.
    """
    result = await Runner.run(enhanced_analytical_agent, user_query)
    
    # Get the raw results
    methods = await extract_methods(user_query)
    application = await apply_methods(user_query, methods)
    
    # Synthesize final response
    synthesis_prompt = f"""
    USER QUERY: {user_query}
    
    EXTRACTED METHODS: {methods}
    
    METHOD APPLICATION: {application}
    
    AGENT RESPONSE: {result.final_output}
    
    Create a comprehensive final response that combines all this information.
    """
    
    final_result = await Runner.run(synthesis_agent, synthesis_prompt)
    return str(final_result.final_output)

# Test function
async def main():
    """Test the enhanced analytical agent."""
    queries = [
        "برای مقایسه قیمت در منطقه ۲۲ با ۱۳ تهران چه کار باید بکنم؟",
        "چگونه می‌توانم ریسک سرمایه‌گذاری در بازار مسکن را ارزیابی کنم؟",
        "بهترین زمان برای خرید ملک در تهران چه زمانی است؟"
    ]
    
    for query in queries:
        print(f"\n{'='*50}")
        print(f"Query: {query}")
        print(f"{'='*50}")
        
        result = await analyze_with_enhanced_agent(query)
        print(result)
        
        # Also save to file
        with open(f"analysis_{hash(query)}.md", "w", encoding="utf-8") as f:
            f.write(f"# Analysis for: {query}\n\n{result}")

if __name__ == "__main__":
    asyncio.run(main()) 
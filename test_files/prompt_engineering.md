# LLM Prompt Engineering Tips

## The Art of Prompting
Getting good results from LLMs is about clear communication. The prompt is 
the interface between human intent and machine output.

## Key Techniques
1. **System prompts**: Set the persona and constraints ("You are a knowledge organizer...")
2. **Few-shot examples**: Show 2-3 examples of desired input/output
3. **Structured output**: Ask for JSON to get parseable responses
4. **Chain of thought**: "Think step by step" improves reasoning
5. **Temperature control**: Lower (0.1-0.3) for factual, higher (0.7-0.9) for creative

## Anti-Patterns
- Vague instructions ("make it better")
- Missing context (expecting the LLM to know your specific domain)
- Ignoring token limits (context window overflow)
- Not validating structured outputs (JSON parsing failures)

## For Classification Tasks (like PARA)
- Provide clear category definitions in the system prompt
- Include examples of each category
- Ask for confidence scores alongside classifications
- Use JSON mode for reliable parsing

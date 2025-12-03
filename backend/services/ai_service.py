import os
import json
import logging
from typing import List, Dict, Any

class AIService:
    """Service for AI-powered content generation"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.enabled = bool(self.api_key)
    
    def generate_task_guidance(self, task_data: Dict) -> List[Dict]:
        """Generate detailed guidance steps using AI"""
        
        if not self.enabled:
            return self._generate_fallback_guidance(task_data)
        
        try:
            import openai
            openai.api_key = self.api_key
            
            prompt = self._create_guidance_prompt(task_data)
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful programming tutor. Generate step-by-step guidance for coding tasks."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            return self._parse_ai_response(content)
            
        except Exception as e:
            logging.error(f"AI guidance generation failed: {e}")
            return self._generate_fallback_guidance(task_data)
    
    def _create_guidance_prompt(self, task_data: Dict) -> str:
        """Create prompt for AI guidance generation"""
        
        title = task_data.get('title', '')
        description = task_data.get('description', '')
        difficulty = task_data.get('difficulty', 'Easy')
        category = task_data.get('category', '')
        
        prompt = f"""
Create step-by-step guidance for this programming task:

Title: {title}
Description: {description}
Difficulty: {difficulty}
Category: {category}

Please provide 3-5 detailed steps in JSON format with this structure:
[
  {{
    "step": 1,
    "title": "Step title",
    "content": "Detailed explanation of what to do",
    "codeExample": "# Code example or template"
  }}
]

Make the guidance beginner-friendly with clear explanations and practical code examples.
"""
        return prompt
    
    def _parse_ai_response(self, content: str) -> List[Dict]:
        """Parse AI response into structured guidance steps"""
        try:
            # Try to extract JSON from the response
            start = content.find('[')
            end = content.rfind(']') + 1
            
            if start != -1 and end != -1:
                json_str = content[start:end]
                return json.loads(json_str)
            else:
                # Fallback parsing
                return self._parse_text_response(content)
                
        except Exception as e:
            logging.error(f"Failed to parse AI response: {e}")
            return []
    
    def _parse_text_response(self, content: str) -> List[Dict]:
        """Parse text response into guidance steps"""
        steps = []
        lines = content.split('\n')
        current_step = None
        
        for line in lines:
            line = line.strip()
            if line.startswith(('Step', '1.', '2.', '3.', '4.', '5.')):
                if current_step:
                    steps.append(current_step)
                
                current_step = {
                    'step': len(steps) + 1,
                    'title': line,
                    'content': '',
                    'codeExample': ''
                }
            elif current_step and line:
                if line.startswith('```') or line.startswith('#'):
                    current_step['codeExample'] += line + '\n'
                else:
                    current_step['content'] += line + ' '
        
        if current_step:
            steps.append(current_step)
        
        return steps
    
    def _generate_fallback_guidance(self, task_data: Dict) -> List[Dict]:
        """Generate fallback guidance when AI is not available"""
        
        title = task_data.get('title', '')
        description = task_data.get('description', '')
        existing_steps = task_data.get('existing_steps', {})
        
        # Use existing steps if available
        if existing_steps:
            guidance_steps = []
            for i, (key, step_content) in enumerate(existing_steps.items(), 1):
                guidance_steps.append({
                    'step': i,
                    'title': f'Step {i}',
                    'content': step_content,
                    'codeExample': self._generate_basic_code_example(step_content)
                })
            return guidance_steps
        
        # Generate basic steps
        return [
            {
                'step': 1,
                'title': 'Understanding the Task',
                'content': f'Let\'s work on "{title}": {description}',
                'codeExample': '# Start by understanding the requirements'
            },
            {
                'step': 2,
                'title': 'Implementation',
                'content': 'Write the code to solve this task step by step.',
                'codeExample': '# Your implementation goes here'
            },
            {
                'step': 3,
                'title': 'Testing',
                'content': 'Test your solution with different inputs to ensure it works correctly.',
                'codeExample': '# Test your code\nprint("Testing...")'
            }
        ]
    
    def _generate_basic_code_example(self, step_content: str) -> str:
        """Generate basic code example based on step content"""
        content_lower = step_content.lower()
        
        if 'variable' in content_lower:
            return 'my_variable = "value"'
        elif 'function' in content_lower:
            return 'def my_function():\n    pass'
        elif 'list' in content_lower:
            return 'my_list = []'
        elif 'print' in content_lower:
            return 'print("Hello, World!")'
        else:
            return '# Your code here'

# Global AI service instance
ai_service = AIService()
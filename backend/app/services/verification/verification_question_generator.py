"""
Verification Question Generator for Step 11.2 - Chain-of-Verification

Generates verification questions from propositions to verify claims independently.

Implements Stage 2 of verification pipeline.
"""
from typing import List
from uuid import uuid4

from app.schemas.verification import VerificationQuestion
from app.schemas.answer import Proposition
from app.core.logging import get_logger

logger = get_logger(__name__)


class VerificationQuestionGenerator:
    """
    Generate verification questions from propositions.

    Uses template-based approach with optional LLM enhancement.
    Ensures questions are focused and test specific factual claims.
    """

    def __init__(self, ollama_client=None):
        """
        Initialize verification question generator.

        Args:
            ollama_client: Optional OllamaClient for LLM-based question generation.
                          If None, uses template-based generation only.
        """
        self.ollama_client = ollama_client
        self.question_templates = self._load_question_templates()

        logger.info(
            f"VerificationQuestionGenerator initialized "
            f"(LLM-enhanced: {ollama_client is not None})"
        )

    def _load_question_templates(self) -> dict:
        """
        Load question templates for different claim types.

        Returns:
            dict: Question templates by type
        """
        return {
            "binary": [
                "According to the documents, is the following statement correct: {claim}?",
                "Do the provided documents confirm that {claim}?",
                "Is it stated in the documents that {claim}?",
            ],
            "factual": [
                "What do the documents say about: {claim}?",
                "Can you verify this claim from the documents: {claim}?",
                "According to the documents, {claim}?",
            ],
            "existence": [
                "Do the documents mention {entity}?",
                "Is {entity} referenced in the provided documents?",
                "According to the documents, does {entity} exist?",
            ]
        }

    async def generate_questions(
        self,
        propositions: List[Proposition]
    ) -> List[VerificationQuestion]:
        """
        Generate verification questions for propositions.

        Creates focused questions to verify each claim independently.

        Args:
            propositions: List of propositions to generate questions for

        Returns:
            List of VerificationQuestion objects

        Example:
            >>> propositions = [
            ...     Proposition(text="Paris is the capital of France", index=0)
            ... ]
            >>> questions = await generator.generate_questions(propositions)
            >>> questions[0].question_text
            'According to the documents, is the following statement correct: ...'
        """
        logger.info(f"Generating verification questions for {len(propositions)} propositions")

        questions = []

        for prop in propositions:
            try:
                # Try LLM-based generation if available
                if self.ollama_client:
                    question = await self._generate_with_llm(prop)
                else:
                    question = self._generate_with_template(prop)

                questions.append(question)

                logger.debug(
                    f"Generated question for proposition {prop.index}",
                    extra={
                        "proposition_index": prop.index,
                        "question_type": question.question_type,
                    }
                )

            except Exception as e:
                logger.warning(
                    f"Failed to generate question for proposition {prop.index}: {e}. "
                    "Using template fallback."
                )
                # Fallback to template
                question = self._generate_with_template(prop)
                questions.append(question)

        logger.info(f"Generated {len(questions)} verification questions")
        return questions

    def _generate_with_template(
        self,
        proposition: Proposition
    ) -> VerificationQuestion:
        """
        Generate verification question using templates.

        Fallback method when LLM is unavailable.

        Args:
            proposition: Proposition to create question for

        Returns:
            VerificationQuestion object
        """
        # Determine question type based on proposition content
        prop_text = proposition.text.lower()

        if any(keyword in prop_text for keyword in ['is', 'are', 'was', 'were']):
            question_type = "binary"
        elif any(keyword in prop_text for keyword in ['what', 'who', 'where', 'when', 'how']):
            question_type = "factual"
        else:
            question_type = "binary"  # Default

        # Select template
        import random
        template = random.choice(self.question_templates[question_type])

        # Format question
        question_text = template.format(claim=proposition.text)

        return VerificationQuestion(
            id=f"vq_{uuid4().hex[:8]}",
            question_text=question_text,
            target_proposition_index=proposition.index,
            question_type=question_type
        )

    async def _generate_with_llm(
        self,
        proposition: Proposition
    ) -> VerificationQuestion:
        """
        Generate verification question using LLM.

        Uses Ollama to create focused verification questions.

        Args:
            proposition: Proposition to create question for

        Returns:
            VerificationQuestion object

        Raises:
            Exception: If LLM generation fails
        """
        prompt = self._build_question_generation_prompt(proposition)

        try:
            response = await self.ollama_client.generate(
                prompt=prompt,
                temperature=0.3,  # Slightly more creative than verification (0.1)
                max_tokens=100,   # Short question
            )

            question_text = response["response"].strip()

            # Validate question
            if not question_text or len(question_text) < 10:
                raise ValueError("Generated question too short")

            # Determine question type from generated text
            question_lower = question_text.lower()
            if question_text.endswith('?') and any(
                word in question_lower for word in ['is', 'are', 'does', 'do']
            ):
                question_type = "binary"
            elif any(word in question_lower for word in ['what', 'who', 'where', 'when', 'how']):
                question_type = "factual"
            else:
                question_type = "binary"

            return VerificationQuestion(
                id=f"vq_{uuid4().hex[:8]}",
                question_text=question_text,
                target_proposition_index=proposition.index,
                question_type=question_type
            )

        except Exception as e:
            logger.error(f"LLM question generation failed: {e}")
            raise

    def _build_question_generation_prompt(
        self,
        proposition: Proposition
    ) -> str:
        """
        Build prompt for LLM to generate verification question.

        Args:
            proposition: Proposition to create question for

        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a fact-checking assistant. Generate a focused verification question to check the following claim against source documents.

CLAIM: {proposition.text}

Generate a single, focused question that:
1. Tests whether this claim is supported by the documents
2. Is answerable with YES/NO or a short factual answer
3. Avoids asking for information not in the claim
4. Is clear and unambiguous

Examples:
- Claim: "Paris is the capital of France"
  Question: "According to the documents, is Paris the capital of France?"

- Claim: "The company was founded in 1985"
  Question: "Do the documents state when the company was founded?"

Generate ONLY the verification question, nothing else.

VERIFICATION QUESTION:"""

        return prompt

import asyncio
from utils.model_loader import ModelLoader
from ragas import SingleTurnSample
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.metrics import LLMContextPrecisionWithoutReference, ResponseRelevancy
import os
model_loader = ModelLoader()


def evaluate_context_precision(query, response, retrieved_context):
    try:
        sample = SingleTurnSample(
            user_input=query,
            response=response,
            retrieved_contexts=retrieved_context,
        )

        async def main():
            os.environ["LLM_PROVIDER"] = "google" 
            llm = model_loader.load_llm()
            evaluator_llm = LangchainLLMWrapper(llm)
            context_precision = LLMContextPrecisionWithoutReference(llm=evaluator_llm)
            result = await context_precision.single_turn_ascore(sample)
            return result

        return asyncio.run(main())
    except Exception as e:
        return e

def evaluate_response_relevancy(query, response, retrieved_context):
    try:
        sample = SingleTurnSample(
            user_input=query,
            response=response,
            retrieved_contexts=retrieved_context,
        )

        llm = model_loader.load_llm()
        embedding_model = model_loader.load_embeddings()   # built here, sync
        evaluator_llm = LangchainLLMWrapper(llm)
        evaluator_embeddings = LangchainEmbeddingsWrapper(embedding_model)

        async def main():
            scorer = ResponseRelevancy(llm=evaluator_llm, 
                                       embeddings=evaluator_embeddings,
                                       strictness=1,   # Groq only supports n=1
            )
            return await scorer.single_turn_ascore(sample)

        return asyncio.run(main())
    except Exception as e:
        return e
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from prompt_library.prompts import PROMPT_REGISTRY, PromptType
from retriever.retrieval import Retriever
from utils.model_loader import ModelLoader
from evaluation.ragas_eval import evaluate_context_precision, evaluate_response_relevancy

retriever_obj = Retriever()
model_loader = ModelLoader()


def format_docs(docs) -> str:
    """Format retrieved documents into a structured text block for the prompt."""
    if not docs:
        return "No relevant documents found."

    formatted_chunks = []
    for d in docs:
        meta = d.metadata or {}
        formatted = (
            f"Title: {meta.get('product_title', 'N/A')}\n"
            f"Price: {meta.get('price', 'N/A')}\n"
            f"Rating: {meta.get('rating', 'N/A')}\n"
            f"Reviews:\n{d.page_content.strip()}"
        )
        formatted_chunks.append(formatted)

    return "\n\n---\n\n".join(formatted_chunks)


def build_chain(query):
    """Build the RAG pipeline chain with retriever, prompt, LLM, and parser."""
    retriever = retriever_obj.load_retriever()
    retrieved_docs=retriever.invoke(query)
    
    retrieved_contexts = [format_docs([doc]) for doc in retrieved_docs]
    
    # retrieved_contexts = [format_docs(retrieved_docs)]
    
    llm = model_loader.load_llm()
    prompt = ChatPromptTemplate.from_template(
        PROMPT_REGISTRY[PromptType.PRODUCT_BOT].template
    )

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain,retrieved_contexts


def invoke_chain(query: str, debug: bool = False):
    """Run the chain with a user query."""
    chain,retrieved_contexts = build_chain(query)

    if debug:
        # For debugging: show docs retrieved before passing to LLM
        docs = retriever_obj.load_retriever().invoke(query)
        print("\nRetrieved Documents:")
        print(format_docs(docs))
        print("\n---\n")

    response = chain.invoke(query)
    
    return retrieved_contexts,response


if __name__=='__main__':
    user_query = "Can you suggest good budget iPhone under 1,00,000 INR?"
   
    retrieved_contexts,response = invoke_chain(user_query)
    
    
    context_score = evaluate_context_precision(user_query,response,retrieved_contexts)
    relevancy_score = evaluate_response_relevancy(user_query,response,retrieved_contexts)
    
    print("\n--- Evaluation Metrics ---")
    print("Context Precision Score:", context_score)
    print("Response Relevancy Score:", relevancy_score)

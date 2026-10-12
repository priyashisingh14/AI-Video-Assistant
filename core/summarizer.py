from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from core.llm_factory import get_llm


def split_transcript(transcript: str) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 3000,
        chunk_overlap = 200
    )

    return splitter.split_text(transcript)

def summarize(transcript: str) -> str:
    llm = get_llm()

    # Fast single-pass summary for standard transcripts (avoids slow multiple API calls)
    if len(transcript) <= 12000:
        single_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an expert meeting summarizer. Provide a concise, professional summary "
                "of the following transcript in bullet points highlighting key points.",
            ),
            ("human", "{text}"),
        ])
        chain = single_prompt | llm | StrOutputParser()
        return chain.invoke({"text": transcript})

    # For very long transcripts, use map-reduce with larger chunks
    chunks = split_transcript(transcript)
    map_prompt = ChatPromptTemplate.from_messages([
        ("system", "Summarize this portion of a meeting transcript concisely in key points."),
        ("human", "{text}"),
    ])
    map_chain = map_prompt | llm | StrOutputParser()
    chunk_summaries = [map_chain.invoke({"text": chunk}) for chunk in chunks]
    combined = "\n\n".join(chunk_summaries)

    combined_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are an expert meeting summarizer. Combine these partial summaries "
            "into one final professional meeting summary in bullet points.",
        ),
        ("human", "{text}"),
    ])
    combined_chain = combined_prompt | llm | StrOutputParser()
    return combined_chain.invoke({"text": combined})

def generate_title(transcript: str) -> str:
    llm = get_llm()

    title_chain = (
        RunnablePassthrough() | RunnableLambda(lambda x: {"text": x}) | 
        ChatPromptTemplate.from_messages([
             (
                "system",
                "Based on the meeting transcript, generate a short professional meeting title "
                "(max 8 words). Only return the title, nothing else.",
            ),
            ("human", "{text}"),
        ])
        | llm
        | StrOutputParser()
    )

    return title_chain.invoke(transcript[:2000])





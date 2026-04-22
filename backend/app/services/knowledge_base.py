"""
Static knowledge base for injecting Tier 1 Verified Facts into the Socratic debate engine,
now utilizing a LangChain RAG pipeline via Chroma.
"""
from typing import Optional
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Note: In a production system, this would be loaded from a persistent database or external API.
VERIFIED_FACTS_DB = {
    "climate change": [
        "February 2026 was the warmest February globally on record, with temperatures 1.3°C above pre-industrial levels (NASA GISS, March 2026).",
        "Atmospheric CO2 concentrations reached 421.3 ppm in February 2026, the highest monthly average ever recorded (NOAA/ESRL, March 2026).",
        "2025 was confirmed as the hottest year on record, with global average temperature 1.55°C above pre-industrial levels (World Meteorological Organization, January 2026).",
        "Arctic sea ice extent in February 2026 was 12.6% below the 1981-2010 average, marking the 7th smallest February extent on record (NSIDC, March 2026).",
        "Extreme weather events caused $312 billion in global damages in 2025, the third highest annual total on record ( reinsurer Munich Re, January 2026).",
        "Sea levels have risen 21.8 cm since 1880, with the rate of increase accelerating to 3.7 mm per year since 2006 (NASA Sea Level Change Team, 2026 data).",
        "Scientists project that without significant emissions reductions, global temperatures could increase by 2.7-3.1°C by 2100 (IPCC AR6 projections, 2021 - still current framework).",
        "Climate models estimate that sea levels could rise 0.3-1.0 meters by 2100 depending on emissions scenarios (NOAA Sea Level Rise Report, 2022 projections)."
    ],
    "economy": [
        "In February 2026, the US inflation rate was 2.4% year-over-year, with core inflation at 2.5% (USAFacts, February 2026).",
        "In February 2026, the US unemployment rate was 4.4% (USAFacts, February 2026).",
        "US GDP growth was 2.9% in 2025, according to the Bureau of Economic Analysis (BEA, February 2026 preliminary estimate).",
        "Federal Reserve interest rates remained at 5.25-5.50% in March 2026 (FOMC meeting minutes, March 2026).",
        "The US federal minimum wage has remained $7.25 per hour since 2009, losing approximately 27% of its real value to inflation (Economic Policy Institute analysis of 2025 data).",
        "US national debt reached $34.0 trillion in February 2026 (Treasury Department Daily Statement, February 2026).",
        "Student loan debt in the US exceeded $1.78 trillion in 2025 (Federal Reserve, January 2026 data).",
        "The Congressional Budget Office projects federal budget deficits will average 6.1% of GDP from 2026-2036 (CBO Long-Term Budget Outlook, February 2026)."
    ],
    "immigration": [
        "In 2022 (latest verified Census data), immigrants made up 13.9% of the total US population (44.8 million people), with 24.0 million being naturalized citizens (US Census Bureau, 2022 American Community Survey).",
        "Unauthorized immigrants constituted approximately 3.2% of the US population (10.5 million people) in 2022 (Pew Research Center, March 2023 analysis of 2022 data).",
        "In 2022, 60% of undocumented immigrants were long-term residents (living in the US for 10+ years), while 40% were recent arrivals (Pew Research Center, March 2023).",
        "Family-based immigration accounted for 64% of new lawful permanent residents in 2022 (DHS Yearbook of Immigration Statistics, 2022).",
        "US Customs and Border Protection encountered 2.4 million migrants at the southern border in 2023 (CBP Yearbook, 2023 data).",
        "Asylum applications reached 1.1 million in 2023, the highest level on record (TRAC Immigration, February 2024 analysis)."
    ],
    "elections": [
        "Voter turnout for the US 2020 presidential election was 66.8%, the highest since 1900, with 158.4 million Americans casting ballots (US Census Bureau, November 2021 report).",
        "Early voting and mail-in voting reached 101.8 million votes in 2020, representing 64% of all votes cast (U.S. Elections Project, final 2020 data).",
        "The 2020 presidential election was certified by all 50 states and the District of Columbia (National Archives, January 2021 certification).",
        "Since 2020, 25 states have enacted new voting laws, with 19 states restricting access and 6 states expanding access (Brennan Center for Justice, February 2026 analysis).",
        "As of March 2026, 44 states have voter ID requirements, with 11 states requiring photo identification (NCSL, March 2026 data).",
        "The 2024 presidential election had approximately 64.2% voter turnout, the second highest since 1900 (Census Bureau preliminary estimates, 2025)."
    ],
    "telecoms": [
        "As of June 2024, 30.2 million Americans (8.9% of population) lacked access to fixed broadband internet at 25/3 Mbps speeds (FCC Broadband Deployment Report, June 2024 data).",
        "The FCC restored net neutrality rules in April 2024, reclassifying broadband as a Title II telecom service (FCC Order, April 2024).",
        "As of 2023, the top 4 broadband providers (Comcast, AT&T, Charter, Verizon) controlled approximately 70% of the US broadband market (Leichtman Research Group, 2023 data).",
        "The average cost of broadband internet was $75.22 per month in 2024, representing 3.2% of median household income (FCC Broadband Deployment Report, June 2024).",
        "As of December 2023, 5G service was available to 75% of the US population, but deployment remains uneven across urban and rural areas (CTIA, December 2023 report).",
        "US average fixed broadband download speeds were 205.4 Mbps in 2024, ranking 12th globally (Ookla Speedtest Global Index, Q4 2024 data)."
    ],
    "healthcare": [
        "As of 2024, approximately 27.6 million Americans remained uninsured, despite coverage gains from the Affordable Care Act (KFF, March 2025 analysis of 2024 data).",
        "Medical debt was the leading cause of personal bankruptcy in the US in 2024, affecting approximately 1 in 5 adults (American Journal of Public Health, 2024 study).",
        "US healthcare costs reached $4.5 trillion in 2024, representing 17.8% of GDP (CMS National Health Expenditure Data, January 2025).",
        "Life expectancy in the US declined for the second consecutive year in 2021 to 76.4 years, the lowest since 1996 (CDC National Vital Statistics System, December 2022 data).",
        "The US maternal mortality rate was 23.8 deaths per 100,000 live births in 2021, with Black women experiencing 2.6 times higher rates than white women (CDC, March 2023 data)."
    ],
    "education": [
        "Student loan debt exceeded $1.78 trillion in 2024, affecting approximately 45 million Americans (Federal Reserve, January 2025 data).",
        "Average published tuition and fees for in-state students at public four-year institutions were $10.980 in 2024-25 (College Board, October 2024 data).",
        "As of 2023, 48 states reported teacher shortages, with approximately 300,000 teachers leaving the profession annually (Learning Policy Institute, 2023 report).",
        "As of 2022, 16% of students (8 million children) lacked adequate home internet access for educational purposes (Common Sense Media, October 2022 report)."
    ],
    "criminal_justice": [
        "As of December 2023, the US incarcerated approximately 1.2 million people in state and federal prisons, with an additional 745,000 in local jails (Bureau of Justice Statistics, December 2023 data).",
        "Black Americans were incarcerated at 5.0 times the rate of white Americans in state prisons as of 2021 (BJS, March 2023 data).",
        "State and local governments spent $82.4 billion on corrections in 2020, with 41 states spending more on corrections than higher education (Prison Policy Initiative, 2023 report).",
        "Police killed 1.247 people in the US in 2023, with Black people being 2.9 times more likely to be killed by police than white people (Mapping Police Violence, January 2024 data)."
    ]
}

_RETRIEVER_INSTANCE = None

def get_rag_retriever():
    global _RETRIEVER_INSTANCE
    if _RETRIEVER_INSTANCE is not None:
        return _RETRIEVER_INSTANCE
        
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    docs = []
    for topic, facts in VERIFIED_FACTS_DB.items():
        for fact in facts:
            docs.append(Document(page_content=fact, metadata={"topic": topic}))
            
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name="verified_facts",
        persist_directory=None # In-memory for evaluation speed
    )
    
    _RETRIEVER_INSTANCE = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 3, "fetch_k": 10}
    )
    return _RETRIEVER_INSTANCE

# Backward compatibility for the evaluator scripts that haven't shifted to pure agents yet
def has_static_kb_for_topic(topic: Optional[str]) -> bool:
    return bool(get_verified_facts_for_topic(topic))

def get_verified_facts_for_topic(topic: Optional[str]) -> list[str]:
    if not topic:
        return []
    retriever = get_rag_retriever()
    docs = retriever.invoke(topic)
    return [doc.page_content for doc in docs]

# --- Ecosystem Scaffold: Document Processing ---

def load_and_split_pdf(file_path: str) -> list[Document]:
    """Demonstrates PDF loading and Recursive Text Splitting."""
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    return splitter.split_documents(docs)

def load_and_split_web(url: str) -> list[Document]:
    """Demonstrates Web scraping and Recursive Text Splitting."""
    loader = WebBaseLoader(url)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    return splitter.split_documents(docs)

def transform_documents(docs: list[Document]) -> list[Document]:
    """Placeholder for Content Transformers (e.g. EmbeddingsRedundantFilter, LLM summarization)."""
    # Simply returns docs unmodified in the baseline scaffold.
    return docs

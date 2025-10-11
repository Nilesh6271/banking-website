import pandas as pd
import numpy as np
import re
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import difflib

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global variables
DATASETS = {
    'definitions': None,
    'deposit_rates': None,
    'loan_rates': None,
    'bank_info': None,
    'forms': None
}

VECTORIZERS = {
    'definitions': None,
    'bank_info': None,
    'deposit_rates': None,
    'loan_rates': None,
    'forms': None
}

EMBEDDING_MODEL = None
THRESHOLD = 0.65  # Minimum confidence threshold

def initialize_chatbot(excel_path):
    """Initialize chatbot with banking datasets and ML models"""
    global DATASETS, VECTORIZERS, EMBEDDING_MODEL
    
    try:
        # Load datasets
        DATASETS['definitions'] = pd.read_excel(excel_path, sheet_name='Definitions')
        DATASETS['deposit_rates'] = pd.read_excel(excel_path, sheet_name='DepositRates')
        DATASETS['loan_rates'] = pd.read_excel(excel_path, sheet_name='LoanRates')
        DATASETS['bank_info'] = pd.read_excel(excel_path, sheet_name='BankInfo')
        DATASETS['forms'] = pd.read_excel(excel_path, sheet_name='Forms')
        
        # Preprocess data - convert all to string
        for name, df in DATASETS.items():
            if df is not None:
                df = df.fillna('').astype(str)
                df = df.applymap(lambda x: x.strip())
        
        # Initialize vectorizers
        VECTORIZERS['definitions'] = TfidfVectorizer(stop_words='english').fit(
            DATASETS['definitions']['Term'] + " " + DATASETS['definitions']['Definition']
        )
        
        VECTORIZERS['bank_info'] = TfidfVectorizer(stop_words='english').fit(
            DATASETS['bank_info']['InfoType'] + " " + DATASETS['bank_info']['Content']
        )
        
        # Deposit rates vectorizer
        deposit_text = DATASETS['deposit_rates'].apply(
            lambda row: f"{row['Product']} {row['Tenure']} {row['Features']}", axis=1
        )
        VECTORIZERS['deposit_rates'] = TfidfVectorizer(stop_words='english').fit(deposit_text)
        
        # Loan rates vectorizer
        loan_text = DATASETS['loan_rates'].apply(
            lambda row: f"{row['LoanType']} {row['SpecialFeatures']}", axis=1
        )
        VECTORIZERS['loan_rates'] = TfidfVectorizer(stop_words='english').fit(loan_text)
        
        # Forms vectorizer
        forms_text = DATASETS['forms'].apply(
            lambda row: f"{row['FormName']} {row['Category']}", axis=1
        )
        VECTORIZERS['forms'] = TfidfVectorizer(stop_words='english').fit(forms_text)
        
        # Load sentence transformer model
        EMBEDDING_MODEL = SentenceTransformer('paraphrase-MiniLM-L6-v2')
        
        logging.info("Chatbot initialized successfully")
        
    except Exception as e:
        logging.error(f"Initialization failed: {str(e)}")
        raise

def get_response(query):
    """Get response for user query with confidence score"""
    # Preserve original query for intent detection
    original_query = query
    clean_query = preprocess_query(query)
    
    # Check for greetings
    if is_greeting(clean_query):
        return "Hello! I'm Apex Bank Assistant. How can I help you today?", 1.0, 'greeting'
    
    # Check for specific intents
    intent, confidence = detect_intent(original_query)
    
    if confidence > THRESHOLD:
        handler = INTENT_HANDLERS.get(intent)
        if handler:
            response, handler_confidence = handler(original_query)
            # Combine intents confidence with handler confidence
            final_confidence = min(confidence, handler_confidence)
            return response, final_confidence, intent
    
    # Fallback to semantic search
    response, confidence, _ = semantic_search(original_query)
    return response, confidence, 'general'

def preprocess_query(query):
    """Clean and normalize user query"""
    query = query.lower().strip()
    query = re.sub(r'[^\w\s]', '', query)  # Remove punctuation
    return query

def is_greeting(query):
    """Check if query is a greeting"""
    greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
    # Split query into words and check exact matches
    words = query.split()
    return any(greeting in words for greeting in greetings)

def detect_intent(query):
    """Detect user intent using hybrid approach"""
    # Convert query to lowercase for case-insensitive matching
    query_lower = query.lower()
    
    # Enhanced intent mapping with priority
    intent_priority = [
        ('forms', ['form', 'download', 'application', 'request', 'need form', 'get form']),
        ('loan_rates', ['loan rate', 'interest on loan', 'emi', 'home loan', 'car loan', 
                        'personal loan', 'business loan', 'education loan', 'gold loan', 'two wheeler']),
        ('deposit_rates', ['fd rate', 'rd rate', 'deposit interest', 'fixed deposit', 
                           'recurring deposit', 'savings rate', 'deposit rate', 'fcnr']),
        ('bank_info', [
            'contact', 'branch', 'timing', 'holiday', 'service', 
            'digital service', 'support', 'help', 'what are', 'offer',
            'how can', 'services', 'about bank', 'bank info', 'nri', 'history',
            'award', 'atm', 'ifsc', 'micr', 'charge', 'fee', 'social media'
        ]),
        ('definition', ['what is', 'meaning of', 'define', 'explain', 'full form']),
    ]
    
    # Check for priority intents first
    for intent, keywords in intent_priority:
        if any(keyword in query_lower for keyword in keywords):
            return intent, 0.85  # High confidence for priority matches
    
    # ML-based detection using embeddings (fallback)
    return ml_intent_detection(query)

def ml_intent_detection(query):
    """Machine learning intent detection with embeddings"""
    intents = list(INTENT_HANDLERS.keys())
    query_embedding = EMBEDDING_MODEL.encode([query])
    
    # Compare against intent examples - updated with your data specifics
    intent_embeddings = EMBEDDING_MODEL.encode([
        "What is an FD?",
        "Current FD rates for senior citizens",
        "Home loan interest rates",
        "Branch timings in Mumbai",
        "Where to download account opening form?",
        "NRI banking services",
        "History of Apex Bank",
        "What is EMI?"
    ])
    
    similarities = cosine_similarity(query_embedding, intent_embeddings)[0]
    max_index = np.argmax(similarities)
    max_similarity = similarities[max_index]
    
    intent_map = {
        0: 'definition',
        1: 'deposit_rates',
        2: 'loan_rates',
        3: 'bank_info',
        4: 'forms',
        5: 'bank_info',  # NRI services
        6: 'bank_info',  # Bank history
        7: 'definition'  # EMI definition
    }
    
    return intent_map.get(max_index, 'general'), max_similarity

def handle_definition(query):
    """Handle definition queries"""
    # Preprocess
    query_clean = preprocess_query(query)
    terms = DATASETS['definitions']['Term'].str.lower().tolist()
    
    # Find best matching term
    best_match = None
    highest_similarity = 0
    
    for term in terms:
        term_embedding = EMBEDDING_MODEL.encode([term])
        query_embedding = EMBEDDING_MODEL.encode([query_clean])
        similarity = cosine_similarity(query_embedding, term_embedding)[0][0]
        
        if similarity > highest_similarity:
            highest_similarity = similarity
            best_match = term
    
    if highest_similarity > THRESHOLD:
        definition = DATASETS['definitions'][
            DATASETS['definitions']['Term'].str.lower() == best_match
        ].iloc[0]
        response = f"{definition['Term']}: {definition['Definition']}\n\n*Example*: {definition['Example']}"
        return response, highest_similarity
    
    return "I'm not sure about that term. Could you rephrase or ask about something else?", 0.4

def handle_deposit_rates(query):
    """Handle deposit rate queries with enhanced matching"""
    # First try to match specific product names
    query_lower = query.lower()
    product_names = DATASETS['deposit_rates']['Product'].str.lower().tolist()
    
    # Create abbreviation map
    abbreviation_map = {
        'fd': 'fixed deposit',
        'rd': 'recurring deposit',
        'fcnr': 'fcnr deposit'
    }
    
    # Replace abbreviations with full names
    for abbr, full in abbreviation_map.items():
        if abbr in query_lower:
            query_lower = query_lower.replace(abbr, full)
    
    # Find best matching product name
    best_match = None
    highest_similarity = 0
    
    for product in product_names:
        product_embedding = EMBEDDING_MODEL.encode([product])
        query_embedding = EMBEDDING_MODEL.encode([query_lower])
        similarity = cosine_similarity(query_embedding, product_embedding)[0][0]
        
        if similarity > highest_similarity:
            highest_similarity = similarity
            best_match = product
    
    # If we have a good match, return all tenures for that product
    if highest_similarity > THRESHOLD:
        product_data = DATASETS['deposit_rates'][
            DATASETS['deposit_rates']['Product'].str.lower() == best_match
        ]
        if not product_data.empty:
            response = f"{best_match.title()} Rates**:\n\n"
            for _, row in product_data.iterrows():
                # Convert rates to percentage format
                gen_rate = float(row['GeneralRate']) * 100
                sen_rate = float(row['SeniorRate']) * 100
                
                response += (
                    f"- *Tenure*: {row['Tenure']}\n"
                    f"  General Rate: {gen_rate:.2f}%\n"
                    f"  Senior Citizen Rate: {sen_rate:.2f}%\n"
                    f"  Minimum Amount: {row['MinAmount']}\n"
                    f"  Features: {row['Features']}\n\n"
                )
            return response, highest_similarity
    
    # If no specific product match, fallback to TF-IDF
    vectorizer = VECTORIZERS['deposit_rates']
    if vectorizer is None:
        return "Deposit rates information is not available.", 0.0
    
    # Prepare dataset text
    deposit_text = DATASETS['deposit_rates'].apply(
        lambda row: f"{row['Product']} {row['Tenure']} {row['Features']}", axis=1
    )
    
    # Transform query and dataset
    query_vec = vectorizer.transform([query])
    deposit_vec = vectorizer.transform(deposit_text)
    
    # Calculate similarities
    similarities = cosine_similarity(query_vec, deposit_vec)[0]
    max_index = np.argmax(similarities)
    max_similarity = similarities[max_index]
    
    if max_similarity > THRESHOLD:
        row = DATASETS['deposit_rates'].iloc[max_index]
        # Convert rates to percentage format
        gen_rate = float(row['GeneralRate']) * 100
        sen_rate = float(row['SeniorRate']) * 100
        
        response = (
            f"{row['Product']}** ({row['Tenure']}):\n"
            f"- General Rate: {gen_rate:.2f}%\n"
            f"- Senior Citizen Rate: {sen_rate:.2f}%\n"
            f"- Minimum Amount: {row['MinAmount']}\n"
            f"- Features: {row['Features']}"
        )
        return response, max_similarity
    
    # Fallback to all deposit products
    response = "*Available Deposit Products*:\n\n"
    for _, row in DATASETS['deposit_rates'].iterrows():
        # Convert rates to percentage format
        gen_rate = float(row['GeneralRate']) * 100
        sen_rate = float(row['SeniorRate']) * 100
        
        response += (
            f"• {row['Product']} ({row['Tenure']}): "
            f"{gen_rate:.2f}% general, "
            f"{sen_rate:.2f}% senior\n"
        )
    return response + "\nPlease specify a product for more details.", 0.7

def handle_loan_rates(query):
    """Ultra-robust loan rate handler that handles all edge cases"""
    try:
        # Normalize query and handle empty cases
        query_lower = query.strip().lower()
        if not query_lower:
            return "Please specify what loan information you're looking for.", 0.7
        
        # Create comprehensive loan mapping with priority scoring
        loan_mapping = [
            # Home loans
            ("home loan", ["home loan", "hl", "housing loan", "property finance", "homeloan"], 1.0),
            ("home loan pro", ["home loan pro", "hl pro", "premium home loan", "pro home loan"], 1.0),
            
            # Vehicle loans
            ("car loan", ["car loan", "auto loan", "vehicle finance", "automobile loan"], 1.0),
            ("two wheeler loan", ["two wheeler", "bike loan", "scooter loan", "motorcycle loan"], 1.0),
            
            # Personal loans
            ("personal loan", ["personal loan", "pl", "unsecured loan", "consumer loan"], 1.0),
            
            # Education loan
            ("education loan", ["education loan", "student loan", "tuition fee loan", "study loan"], 1.0),
            
            # Business loans
            ("business loan", ["business loan", "bl", "commercial loan", "enterprise finance"], 1.0),
            ("msme loan", ["msme loan", "small business loan", "medium enterprise loan"], 0.9),
            
            # Secured loans
            ("gold loan", ["gold loan", "jewelry loan", "ornament loan", "gl"], 1.0),
            ("loan against fd", ["loan against fd", "fd loan", "fixed deposit loan", "loan on deposit", 
                                "against fd", "against fixed deposit"], 1.0),
            ("loan against property", ["loan against property", "lap", "property loan", "mortgage loan", 
                                      "real estate loan", "against property", "against house", "against real estate"], 1.0),
            
            # Mudra loans
            ("mudra loan (shishu)", ["shishu loan", "pmm shishu", "mudra shishu", "micro enterprise loan", 
                                    "muda shishu", "mudra shisu", "mudra shishu"], 0.95),
            ("mudra loan (kishor)", ["kishor loan", "pmm kishor", "mudra kishor", "growing business loan"], 0.95),
            ("mudra loan (tarun)", ["tarun loan", "pmm tarun", "mudra tarun", "established business loan"], 0.95),
            
            # Other loans
            ("pre-approved emi", ["pre-approved emi", "credit card emi", "instant emi"], 0.9),
            ("overdraft", ["overdraft", "od facility", "credit line", "cash credit"], 0.8)
        ]
        
        # Special case handlers - check these first
        if "mudra" in query_lower or "muda" in query_lower:
            return handle_mudra_loans(query_lower)
            
        # Enhanced "against" detection with normalization
        if "against" in query_lower or "againt" in query_lower:
            if "fd" in query_lower or "fixed deposit" in query_lower:
                return handle_loan_against_fd()
            elif ("property" in query_lower or "house" in query_lower or 
                "real estate" in query_lower or "prop" in query_lower):
                return handle_loan_against_property()
        
        # Handle "all loans" requests
        if ("all" in query_lower or "available" in query_lower or "types" in query_lower or 
            "list" in query_lower or "what loans" in query_lower or "which loans" in query_lower):
            return list_all_loans(confidence=0.95)
            
        # Handle "loan rates" without specification
        if ("loan rate" in query_lower or "loan rates" in query_lower or 
            "interest rate" in query_lower or "interest on loan" in query_lower):
            if not any(loan_type in query_lower for _, keywords, _ in loan_mapping for loan_type in keywords):
                return list_all_loans(confidence=0.9)
        
        # Find best loan match using priority scoring
        best_match = None
        highest_score = 0
        
        for loan_type, keywords, base_score in loan_mapping:
            for keyword in keywords:
                # Use word boundaries for better matching
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, query_lower):
                    # Score based on match quality
                    score = base_score
                    
                    # Boost for exact match
                    if f" {keyword} " in f" {query_lower} ":
                        score += 0.1
                    
                    # Boost for "rate" in query
                    if "rate" in query_lower or "interest" in query_lower:
                        score += 0.05
                    
                    if score > highest_score:
                        best_match = loan_type
                        highest_score = score
        
        # Process best match if found
        if best_match:
            return get_loan_details(best_match, confidence=min(highest_score, 1.0))
        
        # Semantic matching as fallback
        loan_types = [loan_type for loan_type, _, _ in loan_mapping]
        best_match, max_similarity = semantic_loan_match(query_lower, loan_types)
        
        if best_match and max_similarity > THRESHOLD:
            return get_loan_details(best_match, confidence=max_similarity)
        
        # Final fallback - list all loans with explanation
        return list_all_loans(confidence=0.85)
    
    except Exception as e:
        logging.error(f"Loan rates processing error: {str(e)}", exc_info=True)
        return "I'm having trouble retrieving loan information. Please contact customer support at 1800-123-4567.", 0.0

def get_loan_details(loan_name, confidence):
    """Get loan details from dataset with multiple fallbacks"""
    # Try exact match first with normalization
    loan_name_clean = re.sub(r'[^\w\s]', '', loan_name.lower().strip())
    
    matching_rows = DATASETS['loan_rates'][
        DATASETS['loan_rates']['LoanType'].str.lower().str.replace(r'[^\w\s]', '').str.strip() == loan_name_clean
    ]
    
    if not matching_rows.empty:
        return format_loan_response(matching_rows.iloc[0], confidence)
    
    # Try case-insensitive substring match
    matching_rows = DATASETS['loan_rates'][
        DATASETS['loan_rates']['LoanType'].str.lower().str.contains(loan_name_clean)
    ]
    
    if not matching_rows.empty:
        return format_loan_response(matching_rows.iloc[0], confidence)
    
    # Try close string match with normalization
    all_loans = DATASETS['loan_rates']['LoanType'].str.lower().str.replace(r'[^\w\s]', '').str.strip().tolist()
    closest = difflib.get_close_matches(loan_name_clean, all_loans, n=1, cutoff=0.7)
    
    if closest:
        matching_rows = DATASETS['loan_rates'][
            DATASETS['loan_rates']['LoanType'].str.lower().str.replace(r'[^\w\s]', '').str.strip() == closest[0]
        ]
        if not matching_rows.empty:
            return format_loan_response(matching_rows.iloc[0], confidence)
    
    # If still not found, try to find related loans
    first_word = loan_name_clean.split()[0] if loan_name_clean else ""
    if first_word:
        related_loans = DATASETS['loan_rates'][
            DATASETS['loan_rates']['LoanType'].str.lower().str.contains(first_word)
        ]
        
        if not related_loans.empty:
            response = f"*Related Loans for '{loan_name.title()}'*:\n\n"
            for _, row in related_loans.iterrows():
                response += (
                    f"• *{row['LoanType']}*: {row['InterestRate']}\n"
                    f"  - Amount: {row['MinAmount']} to {row['MaxAmount']}\n\n"
                )
            return response, confidence * 0.9
    
    # Ultimate fallback - list all loans
    return list_all_loans(confidence=confidence * 0.8)

def handle_mudra_loans(query):
    """Special handler for Mudra loan queries with enhanced detection"""
    # Normalize query for better matching
    query_clean = re.sub(r'[^\w\s]', '', query.lower().strip())
    
    # Detect specific Mudra category with typo tolerance
    mudra_categories = {
        "shishu": ["shishu", "shisu", "shisu", "small", "micro", "startup"],
        "kishor": ["kishor", "kisor", "medium", "growing", "expansion"],
        "tarun": ["tarun", "taran", "established", "larger", "mature"]
    }
    
    found_category = None
    for category, keywords in mudra_categories.items():
        if any(keyword in query_clean for keyword in keywords):
            found_category = category
            break
    
    # Get Mudra loans from dataset
    mudra_loans = DATASETS['loan_rates'][
        DATASETS['loan_rates']['LoanType'].str.lower().str.contains('mudra|muda', case=False)
    ]
    
    # If specific category requested
    if found_category:
        loan_name = f"mudra loan ({found_category})"
        # Try normalized matching
        loan_name_clean = re.sub(r'[^\w\s]', '', loan_name.lower().strip())
        
        specific_loan = mudra_loans[
            mudra_loans['LoanType'].str.lower().str.replace(r'[^\w\s]', '').str.strip() == loan_name_clean
        ]
        
        if not specific_loan.empty:
            return format_loan_response(specific_loan.iloc[0], confidence=0.97)
    
    # Show all Mudra loans if no specific category or category not found
    if not mudra_loans.empty:
        response = "*Pradhan Mantri Mudra Yojana (PMMY) Loan Categories*:\n\n"
        for _, row in mudra_loans.iterrows():
            # Format processing fee
            proc_fee = row['ProcessingFee'].lower()
            proc_fee = "None" if proc_fee in ['nil', 'none', '0', ''] else f"{float(proc_fee)*100:.2f}%"
            
            # Format amount range
            amount_range = f"{row['MinAmount']} to {row['MaxAmount']}"
            
            response += (
                f"• *{row['LoanType']}*:\n"
                f"  - Interest Rate: {row['InterestRate']}\n"
                f"  - Amount Range: {amount_range}\n"
                f"  - Processing Fee: {proc_fee}\n"
                f"  - Features: {row['SpecialFeatures']}\n\n"
            )
        
        return response, 0.95
    
    # Fallback if no Mudra loans found
    return ("Mudra loan details are currently unavailable. "
            "These are government-backed loans for small businesses. "
            "Please visit our website or contact support for more information.", 0.85)

def handle_loan_against_fd():
    """Special handler for loan against FD queries with multiple fallbacks"""
    # Try to get loan details
    loan_name = "loan against fd"
    loan_details = DATASETS['loan_rates'][
        DATASETS['loan_rates']['LoanType'].str.lower().str.contains('against fd|against fixed deposit', case=False)
    ]
    
    if not loan_details.empty:
        return format_loan_response(loan_details.iloc[0], confidence=0.97)
    
    # Try to find the form
    form_details = DATASETS['forms'][
        DATASETS['forms']['FormName'].str.lower().str.contains('against fd|against fixed deposit', case=False)
    ]
    
    if not form_details.empty:
        return f"*Loan Against FD Form*: {form_details.iloc[0]['URL']}", 0.9
    
    # Show related secured loans
    secured_loans = DATASETS['loan_rates'][
        DATASETS['loan_rates']['LoanType'].str.lower().str.contains('against|gold|property', case=False)
    ]
    
    if not secured_loans.empty:
        response = "*Available Secured Loans*:\n\n"
        for _, row in secured_loans.iterrows():
            response += (
                f"• *{row['LoanType']}*: {row['InterestRate']}\n"
                f"  - Amount: {row['MinAmount']} to {row['MaxAmount']}\n\n"
            )
        return response, 0.9
    
    # Ultimate fallback
    return ("Loan Against FD allows you to borrow against your fixed deposits. "
            "Typical interest rates are 2-3% above your FD rate. "
            "Contact us at 1800-123-4567 for details.", 0.8)

def handle_loan_against_property():
    """Special handler for loan against property queries with multiple fallbacks"""
    # Try to get loan details
    loan_name = "loan against property"
    loan_details = DATASETS['loan_rates'][
        DATASETS['loan_rates']['LoanType'].str.lower().str.contains('against property|against house|against real estate', case=False)
    ]
    
    if not loan_details.empty:
        return format_loan_response(loan_details.iloc[0], confidence=0.97)
    
    # Show similar property loans
    property_loans = DATASETS['loan_rates'][
        DATASETS['loan_rates']['LoanType'].str.lower().str.contains('property|house|real estate', case=False)
    ]
    
    if not property_loans.empty:
        response = "*Available Property Loans*:\n\n"
        for _, row in property_loans.iterrows():
            response += (
                f"• *{row['LoanType']}*: {row['InterestRate']}\n"
                f"  - Amount: {row['MinAmount']} to {row['MaxAmount']}\n"
                f"  - Tenure: {row['TenureRange']}\n\n"
            )
        return response, 0.92
    
    # Ultimate fallback
    return ("Loan Against Property (LAP) allows you to borrow against your property. "
            "Typical interest rates range from 8.5% to 11.5% with tenure up to 20 years. "
            "Contact us at 1800-123-4567 for details.", 0.85)

def find_closest_loan_match(loan_name, confidence):
    """Find closest matching loan when exact match fails"""
    all_loans = DATASETS['loan_rates']['LoanType'].str.lower().tolist()
    closest = difflib.get_close_matches(loan_name, all_loans, n=1, cutoff=0.7)
    
    if closest:
        matching_rows = DATASETS['loan_rates'][
            DATASETS['loan_rates']['LoanType'].str.lower() == closest[0]
        ]
        if not matching_rows.empty:
            return format_loan_response(matching_rows.iloc[0], confidence=confidence)
    
    return list_all_loans(confidence=0.85)

def format_loan_response(loan_row, confidence):
    """Format loan information into a response string"""
    # Clean and format data
    loan_type = loan_row['LoanType']
    interest = loan_row['InterestRate']
    amount_range = f"{loan_row['MinAmount']} to {loan_row['MaxAmount']}"
    tenure = loan_row['TenureRange']
    
    # Format processing fee
    proc_fee = loan_row['ProcessingFee'].lower()
    if proc_fee in ['nil', 'none', '0', '']:
        proc_fee = "None"
    else:
        try:
            proc_fee = f"{float(proc_fee) * 100:.2f}%"
        except:
            pass  # Keep original format
    
    # Format prepayment penalty
    prepay_penalty = loan_row['PrepaymentPenalty'].lower()
    if prepay_penalty in ['nil', 'none', '0', '']:
        prepay_penalty = "None"
    else:
        try:
            prepay_penalty = f"{float(prepay_penalty) * 100:.2f}%"
        except:
            pass  # Keep original format
    
    # Build response
    response = (
        f"{loan_type} Details**:\n"
        f"- *Interest Rate*: {interest}\n"
        f"- *Amount Range*: {amount_range}\n"
        f"- *Tenure*: {tenure}\n"
        f"- *Processing Fee*: {proc_fee}\n"
        f"- *Prepayment Penalty*: {prepay_penalty}\n"
        f"- *Features*: {loan_row['SpecialFeatures']}"
    )
    
    return response, confidence

def list_all_loans(confidence):
    """Return list of all available loans"""
    response = "*All Loan Products*:\n\n"
    for _, row in DATASETS['loan_rates'].iterrows():
        response += (
            f"• *{row['LoanType']}*: {row['InterestRate']}\n"
            f"  - Amount: {row['MinAmount']} to {row['MaxAmount']}\n"
            f"  - Tenure: {row['TenureRange']}\n\n"
        )
    return response, confidence

def semantic_loan_match(query, loan_types):
    """Find best loan match using semantic similarity"""
    best_match = None
    highest_similarity = 0
    
    # Get embeddings for all loan types
    loan_embeddings = EMBEDDING_MODEL.encode(loan_types)
    query_embedding = EMBEDDING_MODEL.encode([query])
    
    # Calculate similarities
    similarities = cosine_similarity(query_embedding, loan_embeddings)[0]
    max_index = np.argmax(similarities)
    max_similarity = similarities[max_index]
    
    if max_similarity > THRESHOLD:
        best_match = loan_types[max_index]
    
    return best_match, max_similarity

def handle_bank_info(query):
    """Handle bank information queries with enhanced matching"""
    # Convert to lowercase for matching
    query_lower = query.lower()
    
    # Enhanced direct mapping for common queries
    direct_mapping = {
        'contact': 'Contact Details',
        'digital': 'Digital Services',
        'service': 'Services',
        'support': 'Customer Support',
        'timing': 'Branch Timings',
        'hour': 'Branch Timings',
        'open': 'Branch Timings',
        'holiday': 'Holiday List 2025',
        'close': 'Holiday List 2025',
        'help': 'Customer Support',
        'offer': 'Services',
        'provide': 'Services',
        'about': 'History',
        'history': 'History',
        'award': 'Awards',
        'achieve': 'Awards',
        'atm': 'ATM Network',
        'branch': 'Branch Info',
        'locate': 'Branch Info',
        'ifsc': 'IFSC Code',
        'micr': 'MICR Code',
        'charge': 'Charges',
        'fee': 'Charges',
        'cost': 'Charges',
        'insur': 'Insurance Products',
        'invest': 'Investment Products',
        'secure': 'Security Features',
        'safe': 'Security Features',
        'grievance': 'Grievance Escalation',
        'complain': 'Grievance Escalation',
        'issue': 'Grievance Escalation',
        'nri': 'NRI Services',
        'foreign': 'NRI Services',
        'overseas': 'NRI Services',
        'social': 'Social Media',
        'media': 'Social Media',
        'main': 'Main Branch'
    }
    
    # Check for direct matches
    for keyword, info_type in direct_mapping.items():
        if keyword in query_lower:
            result = DATASETS['bank_info'][
                DATASETS['bank_info']['InfoType'] == info_type
            ]
            if not result.empty:
                response = f"{result.iloc[0]['InfoType']}: {result.iloc[0]['Content']}"
                return response, 0.95
    
    # Use embeddings for better matching
    info_types = DATASETS['bank_info']['InfoType'].tolist()
    info_embeddings = EMBEDDING_MODEL.encode(info_types)
    query_embedding = EMBEDDING_MODEL.encode([query])
    
    similarities = cosine_similarity(query_embedding, info_embeddings)[0]
    max_index = np.argmax(similarities)
    max_similarity = similarities[max_index]
    
    if max_similarity > THRESHOLD:
        info_type = info_types[max_index]
        result = DATASETS['bank_info'][DATASETS['bank_info']['InfoType'] == info_type]
        if not result.empty:
            response = f"{result.iloc[0]['InfoType']}: {result.iloc[0]['Content']}"
            return response, max_similarity
    
    # Fallback to semantic search
    response, confidence, _ = semantic_search(query)
    return response, confidence

def handle_forms(query):
    """Handle form requests with TF-IDF matching"""
    vectorizer = VECTORIZERS['forms']
    if vectorizer is None:
        return "Forms information is not available.", 0.0
    
    # Prepare dataset text
    form_text = DATASETS['forms'].apply(
        lambda row: f"{row['FormName']} {row['Category']}", axis=1
    )
    
    # Transform query and dataset
    query_vec = vectorizer.transform([query])
    form_vec = vectorizer.transform(form_text)
    
    # Calculate similarities
    similarities = cosine_similarity(query_vec, form_vec)[0]
    max_index = np.argmax(similarities)
    max_similarity = similarities[max_index]
    
    if max_similarity > THRESHOLD:
        row = DATASETS['forms'].iloc[max_index]
        qr_status = '✅ Available' if row['QRCode'] == 'Yes' else '❌ Not available'
        response = (
            f"{row['FormName']}\n"
            f"Download: {row['URL']}\n"
            f"QR Code: {qr_status}"
        )
        return response, max_similarity
    
    # Fuzzy match for form names
    form_names = DATASETS['forms']['FormName'].tolist()
    closest_match = difflib.get_close_matches(query, form_names, n=1, cutoff=0.5)
    
    if closest_match:
        row = DATASETS['forms'][
            DATASETS['forms']['FormName'] == closest_match[0]
        ].iloc[0]
        qr_status = '✅ Available' if row['QRCode'] == 'Yes' else '❌ Not available'
        response = (
            f"{row['FormName']}\n"
            f"Download: {row['URL']}\n"
            f"QR Code: {qr_status}"
        )
        return response, 0.8
    
    # Fallback to list of popular forms
    response = "*Available Forms*:\n\n"
    for _, row in DATASETS['forms'].head(5).iterrows():
        response += f"• {row['FormName']} ({row['Category']})\n"
    return response + "\nPlease specify the form name for direct download.", 0.6

def semantic_search(query):
    """Fallback semantic search across all datasets"""
    best_response = "I'm sorry, I couldn't find information about that. " \
                   "Please try rephrasing or contact customer support at 1800-123-4567."
    highest_confidence = 0
    
    # Search across all datasets
    for dataset_name, dataset in DATASETS.items():
        if dataset is None or dataset.empty:
            continue
            
        # Create combined text for each row
        if dataset_name == 'definitions':
            text = dataset['Term'] + " " + dataset['Definition']
        elif dataset_name in ['deposit_rates', 'loan_rates']:
            text = dataset.apply(lambda row: ' '.join(str(x) for x in row), axis=1)
        else:
            text = dataset.apply(lambda row: ' '.join(str(x) for x in row), axis=1)
        
        # Vectorize and compare
        vectorizer = VECTORIZERS.get(dataset_name)
        if vectorizer is None:
            continue
            
        try:
            query_vec = vectorizer.transform([query])
            content_vec = vectorizer.transform(text)
            
            similarities = cosine_similarity(query_vec, content_vec)[0]
            max_index = np.argmax(similarities)
            max_similarity = similarities[max_index]
            
            if max_similarity > highest_confidence and max_similarity > THRESHOLD/2:
                highest_confidence = max_similarity
                row = dataset.iloc[max_index]
                
                if dataset_name == 'definitions':
                    best_response = f"{row['Term']}: {row['Definition']}\n\n*Example*: {row['Example']}"
                elif dataset_name == 'deposit_rates':
                    # Convert rates to percentage format
                    gen_rate = float(row['GeneralRate']) * 100
                    sen_rate = float(row['SeniorRate']) * 100
                    best_response = (
                        f"{row['Product']}** ({row['Tenure']}):\n"
                        f"- General Rate: {gen_rate:.2f}%\n"
                        f"- Senior Citizen Rate: {sen_rate:.2f}%"
                    )
                elif dataset_name == 'loan_rates':
                    best_response = f"{row['LoanType']}: Interest Rate {row['InterestRate']}"
                elif dataset_name == 'bank_info':
                    best_response = f"{row['InfoType']}: {row['Content']}"
                elif dataset_name == 'forms':
                    best_response = f"{row['FormName']}: {row['URL']}"
        except Exception as e:
            logging.error(f"Semantic search error in {dataset_name}: {str(e)}")
            continue
    
    return best_response, highest_confidence, 'general'

# Intent handler mapping
INTENT_HANDLERS = {
    'definition': handle_definition,
    'deposit_rates': handle_deposit_rates,
    'loan_rates': handle_loan_rates,
    'bank_info': handle_bank_info,
    'forms': handle_forms
}
import openai
import streamlit as st
from io import BytesIO
import base64
import numpy as np
from streamlit.components.v1 import html

# Initialize OpenAI client
client = openai.Client(api_key=st.secrets.get("OPENAI_API_KEY"))

# Load the password from Streamlit secrets
APP_PASSWORD = st.secrets.get("APP_PASSWORD")

# Check if the API key is available
if not client.api_key:
    st.warning("Por favor, insira sua chave API OpenAI para continuar.")
    st.stop()

# Check if the user is logged in
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Function to display the login page
def login_page():
    st.markdown("<h1 style='color: green;'>Asclepius DSGU Login</h1>", unsafe_allow_html=True)
    password = st.text_input("Digite a senha:", type="password")
    if st.button("Login"):
        if password == APP_PASSWORD:
            st.session_state.logged_in = True
            st.experimental_rerun()
        else:
            st.error("Senha incorreta. Por favor, tente novamente.")

def copy_to_clipboard_button(text, button_text="Copiar conteúdo"):
    """
    Create a button that copies the given text to clipboard when clicked.
    
    :param text: The text to be copied to clipboard
    :param button_text: The text to display on the button
    :return: None
    """
    # Encode the text to make it safe for passing to JavaScript
    encoded_text = text.replace("'", "\\'").replace("\n", "\\n")
    
    # JavaScript function to copy text to clipboard
    js_code = f"""
    <script>
    function copyToClipboard() {{
        const text = '{encoded_text}';
        navigator.clipboard.writeText(text).then(function() {{
            console.log('Text successfully copied to clipboard');
            alert('Copied to clipboard!');
        }}).catch(function(err) {{
            console.error('Could not copy text: ', err);
            alert('Failed to copy text. Please try again.');
        }});
    }}
    </script>
    <button onclick="copyToClipboard()">{button_text}</button>
    """
    
    # Render the button using Streamlit's html component
    html(js_code, height=50)

# Function to display the main content
def main_page():
    # Content for instruction files in Portuguese
    system_01_intake = """
    # MISSÃO
    Você é um chatbot de recepção de dados de paciente focado em sintomas, os dados serão fornecidos pelo médico, e esse é um ambulatório de urologia e nefrologia. Sua missão é fazer perguntas para ajudar o médico e auxiliar a articular completamente a consulta de maneira clara. Sua transcrição de chat será, em última instância, traduzida em notas de prontuário.

    # REGRAS
    Faça apenas uma pergunta de cada vez. Forneça algum contexto ou esclarecimento em torno das perguntas de acompanhamento que você faz. Não converse com o médico. Seu tom deve ser amigável e de sugestão, você deve sugerir as perguntas, por exemplo: "Que tal perguntar se o paciente já sentiu sintoma X?". As perguntas e a consulta em si são de uma especialidade, logo devem focar no sistema genitourinário.
    """

    system_02_prepare_notes = """
    # MISSÃO
    Você é um bot de registro que receberá uma transcrição de recepção de dados do paciente. Você deve traduzir o registro do chat em notas médicas detalhadas para o médico.

    # ESQUEMA DE INTERAÇÃO
    O USUÁRIO lhe fornecerá a transcrição. Seu resultado será uma lista de notas hifenizadas. Certifique-se de capturar os sintomas e qualquer informação relevante de maneira ordenada e estruturada. Você gerará um relatório com o seguinte formato:
    
    # FORMATO DO RELATÓRIO

    1. IDENTIFICAÇÃO
        - <Forneça dados de identificação do paciente se forem providos pelo USUÁRIO, tais como nome, sexo, idade, etc>

    2. QUEIXA PRINCIPAL
        - <Escreva a queixa principal do paciente, se fornecida pelo USUÁRIO, nas palavras do paciente>
    
    3. HISTÓRIA ATUAL DA DOENÇA
        - <Escreva a história atual da doença com foco no sistema genitourinário, isto é, os achados médicos fornecidos e encontrados pelo USUÁRIO. Use sempre linguagem técnica e médica para descrever os sinais e sintomas, em ordem cronológica.>
    
    4. HISTÓRIA PATOLÓGICA PREGRESSA
        - <Escreva a história patológica pregressa do paciente, utilizando linguagem médica técnica, se fornecida pelo USUÁRIO. Caso não sejam fornecidos dados suficientes, descreva apenas como "dados insuficientes">

    5. HISTÓRIA FISIOLÓGICA DO(A) PACIENTE
        - <Escreva os dados relativos a história fisiológica do paciente, se possui vacinação em dia, etc. Caso não sejam fornecidos dados suficientes, descreva apenas como "dados insuficientes">
    
    6. HISTÓRICO FAMILIAR
        - <Escreva os dados relativos ao histórico médico patológico do(a) paciente, se possuem alguma patologia digna de nota como diabetes, hipertensão, etc>
    
    7. HÁBITOS DE VIDA
        - <Escreva os hábitos de vida do paciente, se é sedentário ou ativo fisicamente, se pratica etilismo ou tabagismo, etc>
    
    8. ISDA (REVISÃO DOS SISTEMAS)
        - <Escreva uma lista com marcadores dos sistemas do paciente e se possuem algum sintoma relacionado a eles, por exemplo "NEUROLÓGICO: Cefaleia" etc>
    
    9. EXAME FÍSICO
        - <Descreva os dados do exame físico conforme fornecidos pelo USUÁRIO. Deve ser descrito por uma lista com marcadores, seguindo a ordem do exemplo abaixo:
        "- ECTOSCOPIA: Paciente em BEG (bom estado geral), vígil, orientado no tempo e espaço, fáceis atípica, normocorado, acianótico, anictérico, perfundido, hidratado, nutrido, sem linfonodomegalias, pulsos presentes e simétricos. MMII (membros inferiores) – pulsos presentes e simétricos, perfundido, sem sinais de TVP e livre de edemas.
        - AUSCULTA RESPIRATÓRIA: Murmúrio vesicular presente, sem ruídos adventícios, 19 IRPM.
        - AUSCULTA CARDIOVASCULAR: Ritmo cardíaco regular, em 2 tempos, bulhas normofonéticas, sem sopros ou estalidos.
        - ABDOME: Plano, flácido, indolor à palpação superficial e profunda, sem massas palpáveis, traube livre.
        - NEUROLÓGICO: ECG 15, sem déficits focais." Caso o USUÁRIO não forneça dados de exame físico, deve ser utilizado o exemplo fornecido no lugar. Sempre forneça o exame físico completo, substituindo as informações não fornecidas pelo exemplo citado>
    """

    system_03_diagnosis = """
    # MISSÃO
    Você é um bot de notas médicas que receberá um prontuário ou sintomas de um paciente logo após a recepção. Você gerará uma lista dos diagnósticos mais prováveis ou vias de investigação para o médico seguir, com foco no sistema genitourinário.

    # ESQUEMA DE INTERAÇÃO
    O USUÁRIO lhe fornecerá as notas médicas. Você gerará um relatório com o seguinte formato:

    # FORMATO DO RELATÓRIO

    1. <DIAGNÓSTICO POTENCIAL EM LETRAS MAIÚSCULAS>: <Descrição da condição, nomes alternativos comuns, etc>
       - DIFERENCIAIS: <Descrição dos diferenciais>
       - DEMOGRAFIA: <Demografia típica de afecção, fatores de risco demográficos>
       - SINTOMAS: <Lista formal de sintomas>
       - INDICADORES: <Por que este paciente corresponde a este diagnóstico>
       - CONTRAINDICADORES: <Por que este paciente não corresponde a este diagnóstico>
       - PROGNÓSTICO: <Perspectiva geral da condição>
       - TRATAMENTO: <Opções de tratamento disponíveis>
       - TESTES: <Testes de acompanhamento recomendados e o que você está procurando, informações probativas desejadas>

    2. <DIAGNÓSTICO POTENCIAL EM LETRAS MAIÚSCULAS>: <Descrição da condição, nomes alternativos comuns, etc>
       - DIFERENCIAIS: <Descrição dos diferenciais>
       - DEMOGRAFIA: <Demografia típica de afecção, fatores de risco demográficos>
       - SINTOMAS: <Lista formal de sintomas>
       - INDICADORES: <Por que este paciente corresponde a este diagnóstico>
       - CONTRAINDICADORES: <Por que este paciente não corresponde a este diagnóstico>
       - PROGNÓSTICO: <Perspectiva geral da condição>
       - TRATAMENTO: <Opções de tratamento disponíveis>
       - TESTES: <Testes de acompanhamento recomendados e o que você está procurando, informações probativas desejadas>
    """

    system_04_clinical = """
    # MISSÃO
    Você é um bot de recepção médica. Você está se preparando para a etapa final antes que o profissional médico especialista em urologia ou nefrologia avalie o paciente em um ambiente clínico. Você receberá notas da recepção do paciente, bem como vias de investigação diagnóstica geradas pelo sistema. Você deve preparar algumas recomendações clínicas para avaliar o paciente. Lembre-se de que esta é uma consulta de especialidade (urologia e nefrologia).

    # SENTIDOS
    Visão, audição, olfato, tato (palpação) e outros testes clínicos. Quais sentidos o profissional médico deve estar atento? Dadas as notas, seja específico e probativo em suas recomendações. Certifique-se de explicar o que procurar, bem como por que isso pode ser útil.

    # EXAME CLÍNICO
    Liste técnicas específicas de exame que você recomenda, bem como o que procurar e por que. Lembre-se de que isso é estritamente para a visita clínica. Nos preocuparemos com encaminhamentos e acompanhamento mais tarde. Concentre-se apenas em técnicas de cuidados primários.

    # PERGUNTAS DE ENTREVISTA
    Sugira várias perguntas para o clínico fazer ao paciente como parte da investigação.

    # FORMATO DE SAÍDA
    Independentemente do formato de entrada (você pode receber notas, prontuários, registros de chat, etc.), seu formato de saída deve ser consistente e usar o seguinte:

    ## SENTIDOS

    VISÃO: <O que procurar ao envolver-se visualmente com o paciente. Explique por que esta informação pode ser probativa.>

    AUDIÇÃO: <O que ouvir ao envolver-se com o paciente. Explique por que esta informação pode ser probativa.>

    TATO: <Quais sensações físicas, se houver, procurar ao palpar. Explique por que esta informação pode ser probativa.>

    OLFATO: <Quais cheiros prestar atenção, se houver algum relevante. Explique por que esta informação pode ser probativa.>

    ## EXAME

    - <TÉCNICA DE EXAME EM LETRAS MAIÚSCULAS>: <Descrição do que procurar e por que, por exemplo, como este exame é probativo>
    - <TÉCNICA DE EXAME EM LETRAS MAIÚSCULAS>: <Descrição do que procurar e por que, por exemplo, como este exame é probativo>
    - <TÉCNICA DE EXAME EM LETRAS MAIÚSCULAS>: <Descrição do que procurar e por que, por exemplo, como este exame é probativo>

    ## ENTREVISTA

    - <PROPÓSITO PROBATIVO DA PERGUNTA EM LETRAS MAIÚSCULAS>: "<Pergunta sugerida>?"
    - <PROPÓSITO PROBATIVO DA PERGUNTA EM LETRAS MAIÚSCULAS>: "<Pergunta sugerida>?"
    - <PROPÓSITO PROBATIVO DA PERGUNTA EM LETRAS MAIÚSCULAS>: "<Pergunta sugerida>?"
    """

    system_05_referrals = """
    # MISSÃO
    Você é um bot clínico médico. Você receberá notas médicas, prontuários ou outros registros do paciente ou do clínico. Seu trabalho principal é recomendar exames complementares, levando em consideração que é uma consulta de especialidade (urologia ou nefrologia).

    # FORMATO DO RELATÓRIO
    Seu relatório deve seguir este formato:

    ## EXAMES COMPLEMENTARES

    - <TIPO DE EXAME COMPLEMENTAR>: <Descrição do trabalho a ser feito, por exemplo, imagem, flebotomia, etc., bem como valor probativo, por exemplo, indicações, contraindicações, diferenciais, em outras palavras, o que você está tentando confirmar ou descartar>
    - <TIPO DE EXAME COMPLEMENTAR>: <Descrição do trabalho a ser feito, por exemplo, imagem, flebotomia, etc., bem como valor probativo, por exemplo, indicações, contraindicações, diferenciais, em outras palavras, o que você está tentando confirmar ou descartar>
    """

    system_06_conduct = """
    # MISSÃO
    Você é um bot de conduta médica. Sua tarefa é sugerir uma conduta médica baseada em todas as informações anteriores dos sistemas de recepção, notas médicas, diagnóstico, avaliação clínica e encaminhamentos.

    # ESQUEMA DE INTERAÇÃO
    O USUÁRIO lhe fornecerá todas as notas médicas e relatórios anteriores. Sua saída deve ser uma lista detalhada de condutas médicas recomendadas para o paciente, considerando o diagnóstico, avaliação clínica e encaminhamentos.

    # FORMATO DO RELATÓRIO

    1. <NOME DA CONDUTA EM LETRAS MAIÚSCULAS>: <Descrição da conduta recomendada, sendo sempre iniciada com um verbo de ação, como "conduzo, solicito, prescrevo">
       - MOTIVAÇÃO: <Razão pela qual esta conduta é recomendada>
       - OBJETIVOS: <Objetivos específicos desta conduta>
       - PROCEDIMENTOS: <Procedimentos a serem seguidos>
       - MONITORAMENTO: <Métodos de monitoramento e avaliação da eficácia da conduta>
       - AJUSTES: <Possíveis ajustes na conduta baseada na resposta do paciente>

    2. <NOME DA CONDUTA EM LETRAS MAIÚSCULAS>: <Descrição da conduta recomendada, sendo sempre iniciada com um verbo de ação, como "conduzo, solicito, prescrevo">
       - MOTIVAÇÃO: <Razão pela qual esta conduta é recomendada>
       - OBJETIVOS: <Objetivos específicos desta conduta>
       - PROCEDIMENTOS: <Procedimentos a serem seguidos>
       - MONITORAMENTO: <Métodos de monitoramento e avaliação da eficácia da conduta>
       - AJUSTES: <Possíveis ajustes na conduta baseada na resposta do paciente>
    """
    system_07_prescription = """
    # MISSÃO
    Você é um bot de prescrição médica. Sua tarefa é gerar uma prescrição médica com base nos principais sintomas e diagnósticos prováveis fornecidos pelos demais sistemas. 
    SEMPRE leve em consideração as comorbidades, doenças de base e alergias na hora de escolher medicações, atentando-se as contraindicações de cada uma.
    
    # ESQUEMA DE INTERAÇÃO
    Com base nos sintomas principais e diagnósticos prováveis feitos durante a anamnese fornecida. Sua saída deve ser uma prescrição médica detalhada.

    # FORMATO DO RELATÓRIO

    PRESCRIÇÃO MÉDICA

    Data: <Data atual>

    Nome do Paciente: <Nome do paciente, se fornecido>

    1. <NOME DO MEDICAMENTO>
       - Dosagem: <Dosagem recomendada>
       - Frequência: <Frequência de administração>
       - Duração: <Duração do tratamento>
       - Instruções especiais: <Quaisquer instruções específicas para a administração>

    2. <NOME DO MEDICAMENTO>
       - Dosagem: <Dosagem recomendada>
       - Frequência: <Frequência de administração>
       - Duração: <Duração do tratamento>
       - Instruções especiais: <Quaisquer instruções específicas para a administração>

    RECOMENDAÇÕES ADICIONAIS:
    - <Qualquer recomendação adicional ou cuidados especiais>
"""

    # Initialize session state
    if "conversation" not in st.session_state:
        st.session_state.conversation = [{'role': 'system', 'content': system_01_intake}]

    if "user_messages" not in st.session_state:
        st.session_state.user_messages = []

    if "all_messages" not in st.session_state:
        st.session_state.all_messages = []

    if "transcription" not in st.session_state:
        st.session_state.transcription = ""

    if "image_analysis" not in st.session_state:
        st.session_state.image_analysis = []

    # Function to call OpenAI API
    def chatbot(conversation, model="gpt-4o-mini", temperature=0, max_tokens=3000):
        response = client.chat.completions.create(
            model=model, 
            messages=conversation, 
            temperature=temperature, 
            max_tokens=max_tokens
        )
        text = response.choices[0].message.content
        return text

    # Chatbot interaction
    st.markdown("<h1 style='color: green;'>Asclepius DSGU</h1>", unsafe_allow_html=True)

    # Display the HTML and JavaScript code
    html(js_code, height=100)

    st.header("Descreva o caso clínico. Digite PRONTO quando terminar.")
    if prompt := st.text_area("Luis:", height=200):
        if prompt.strip().upper() != "PRONTO" and prompt.strip().upper() != "PRESCRIÇÃO":
            st.session_state.user_messages.append(prompt)
            st.session_state.all_messages.append(f'Luis: {prompt}')
            st.session_state.conversation.append({'role': 'user', 'content': prompt})

            response = chatbot(st.session_state.conversation)
            st.session_state.conversation.append({'role': 'assistant', 'content': response})
            st.session_state.all_messages.append(f'Asclepius: {response}')
            st.write(f'**Asclepius:** {response}')
        elif prompt.strip().upper() == "PRONTO":
            st.write("Consegui os dados. Gerando notas e relatórios...")

            # Include transcription and image analysis in the notes
            all_input = '\n\n'.join(st.session_state.all_messages)
            if st.session_state.transcription:
                all_input += f"\n\nAudio Transcription:\n{st.session_state.transcription}"
            if st.session_state.image_analysis:
                all_input += f"\n\nImage Analysis:\n" + "\n".join(st.session_state.image_analysis)

            # Generate Intake Notes
            st.write("**Gerando anamnese...**")
            notes_conversation = [{'role': 'system', 'content': system_02_prepare_notes}]
            notes_conversation.append({'role': 'user', 'content': all_input})
            notes = chatbot(notes_conversation)
            st.write(f'**Versão das notas da conversa:**\n\n{notes}')
            copy_to_clipboard_button(notes, "Copiar anamnese")

            # Generate Hypothesis Report
            st.write("**Gerando Relatório de Hipóteses...**")
            report_conversation = [{'role': 'system', 'content': system_03_diagnosis}]
            report_conversation.append({'role': 'user', 'content': notes})
            report = chatbot(report_conversation)
            st.write(f'**Relatório de Hipóteses:**\n\n{report}')
            copy_to_clipboard_button(report, "Copiar hipótese diagnóstica")

            # Prepare for Clinical Evaluation
            st.write("**Preparando para Avaliação Clínica...**")
            clinical_conversation = [{'role': 'system', 'content': system_04_clinical}]
            clinical_conversation.append({'role': 'user', 'content': notes})
            clinical = chatbot(clinical_conversation)
            st.write(f'**Avaliação Clínica:**\n\n{clinical}')

            # Generate Referrals and Tests
            st.write("**Gerando Encaminhamentos e Exames Complementares...**")
            referrals_conversation = [{'role': 'system', 'content': system_05_referrals}]
            referrals_conversation.append({'role': 'user', 'content': notes})
            referrals = chatbot(referrals_conversation)
            st.write(f'**Encaminhamentos e Exames Complementares:**\n\n{referrals}')
            copy_to_clipboard_button(referrals, "Copiar encaminhamentos")

            # Generate Suggested Medical Conduct
            st.write("**Gerando Conduta Médica Sugerida...**")
            conduct_conversation = [{'role': 'system', 'content': system_06_conduct}]
            conduct_conversation.append({'role': 'user', 'content': notes})
            conduct = chatbot(conduct_conversation)
            st.write(f'**Conduta Médica Sugerida:**\n\n{conduct}')
        
            st.session_state.notes = notes
        elif prompt.strip().upper() == "PRESCRIÇÃO":
            st.write("Gerando prescrição médica...")

            # Generate Prescription
    prescription_conversation = [{'role': 'system', 'content': system_07_prescription}]
    if 'notes' in st.session_state:
        prescription_conversation.append({'role': 'user', 'content': st.session_state.notes})
        prescription = chatbot(prescription_conversation)
        st.write(f'**Prescrição Médica:**\n\n{prescription}')
        copy_to_clipboard_button(prescription, "Copiar prescrição")

# Main Execution Flow
if st.session_state.logged_in:
    main_page()
else:
    login_page()
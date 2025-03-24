# reviewer

## Project Overview

This project aims to develop an application with a basic frontend where users can upload a PDF, typically a research paper. The application will then:

1. Convert the uploaded PDF to HTML, ensuring that mathematical formulas and other specialized content are accurately extracted.
2. Fetch the top 5 most cited papers referenced in the uploaded article.
3. Use the uploaded article and the top 5 cited papers as domain knowledge, which will be fed to a large language model (LLM) via the OpenAI API.
4. Allow users to hover over text within the HTML, which will act as a question. The answer to the question will be fetched from the OpenAI API, augmented with the domain knowledge.

## Features

- **PDF to HTML Conversion**: Accurate extraction of text, images, and mathematical formulas.
- **Citation Analysis**: Identification and retrieval of the top 5 most cited papers.
- **Domain Knowledge Integration**: Use of the uploaded paper and its top citations as context for the LLM.
- **Interactive Q&A**: Hover-based interaction to fetch answers from the LLM.

## Technologies

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Python, Flask/Django
- **PDF Processing**: PyMuPDF, pdfminer.six
- **Citation Analysis**: Semantic Scholar API, CrossRef API
- **LLM Integration**: OpenAI API

## Setup Instructions

1. Clone the repository.
2. Install the required dependencies.
3. Set up API keys for OpenAI and citation analysis services.
4. Run the application.

## Usage

1. Upload a PDF research paper.
2. View the converted HTML with interactive elements.
3. Hover over text to get answers from the LLM, augmented with domain knowledge.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License.
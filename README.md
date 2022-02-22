# stock_tax
Reads a PDF report or a CSV report from E-Trade and creates a form that is similar to form 8949 as described in the instructions for form 8949(exception 2).

The modules that are used in this code are FPDF, PyPDF2, and csv. To use this program, you may need to download those modules.

** DISCLAIMER **

This code is not perfect. While it has worked for the tests I have used, it may not work for other reports. Use at your own risk. I am not responsible for your actions(meaning that no legal action can be taken against me).

If there are any errors or mistakes, it would be great if you could inform me. I would love to improve the code, as I know it is not perfect.

There are 2 versions that can process both PDF reports and CSV reports: "REAL_pdf_csv_python2.py" and "REAL_pdf_csv_python3.py"

To use these, you must first choose which type of reports you are inputting(PDF or CSV), then enter the necessary information(including the names of the files). Remember to include the file name extension when entering your file names(also your files should be in the same directory as this code).

The output files should be PDFs that are separated by length(short or long).

Once again, this tool is not too developed, and has not been tested for many test cases, so use at your own risk.

This code may be used for individual usage, but may not be used for commercial use.

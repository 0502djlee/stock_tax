import PyPDF2
import csv
import time
from fpdf import FPDF


test_mode = True 


def is_valid_num(num):
    if(num == "N/A"):
        return True
    if (num[0] == "$" or num[0] == "(" or num[0] == "0" or num[0] == "1" or num[0] == "2" or num[0] == "3" or num[0] == "4" or num[0] == "5" or num[0] == "6" or num[0] == "7" or num[0] == "8" or num[0] == "9"):
        if (num[1] == "$" or num[1] == "," or num[1] == "." or num[1] == "0" or num[1] == "1" or num[1] == "2" or num[1] == "3" or num[1] == "4" or num[1] == "5" or num[1] == "6" or num[1] == "7" or num[1] == "8" or num[1] == "9"):
            if (num[2] == "$" or num[2] == "/" or num[2] == "," or num[2] == "." or num[2] == ")" or num[2] == "0" or num[2] == "1" or num[2] == "2" or num[2] == "3" or num[2] == "4" or num[2] == "5" or num[2] == "6" or num[2] == "7" or num[2] == "8" or num[2] == "9"):
                return True
    return False

def stringify_no_round(num):
    if num < 0:
        return "(" + "{0:,}".format(-1*num) + ")"
    else:
        return "{0:,}".format(num)

def stringify_two_decimals(num):
    if num < 0:
        return "(" + "{0:,.2f}".format(-1*num) + ")"
    else:
        return "{0:,.2f}".format(num)


class Transaction:
    def __init__(self, symbol, shares, date_acquired, date_sold, proceeds, cost_basis, accrued_market_discount, wash_sale_amount, gain, length):
        self.__symbol = symbol
        self.__shares = float(shares.replace(',', ''))
        self.__date_acquired = date_acquired
        self.__date_sold = date_sold
        proceeds = proceeds.strip("$").replace(',', '')
        self.__proceeds = float(proceeds.replace(',', ''))
        if(cost_basis == "N/A" or cost_basis == "--"):
            self.__cost_basis = 0.0
        else:
            cost_basis = cost_basis.strip("$").replace(',', '')
            if cost_basis=="0.00":
                print("Cost Basis not found. This might be ESPP. Need to check...")
                self.__cost_basis = 0.0
            else:
                self.__cost_basis = float(cost_basis)

        if(accrued_market_discount == "N/A" or accrued_market_discount == "--"):
            self.__accrued_market_discount = 0.0
        else:
            accrued_market_discount = accrued_market_discount.strip("$").replace(',', '')
            self.__accrued_market_discount = float(accrued_market_discount)

        if(gain == "N/A" or gain == "--"):
            self.__gain = 0.0
        else:
            if gain[0]=='(':
                gain = gain.strip("()$").replace(',', '')
                self.__gain = -float(gain)
            else:
                gain = gain.strip("$").replace(',', '')
                self.__gain = float(gain)

        if(wash_sale_amount == "N/A" or wash_sale_amount == "--"):
            self.__wash_sale_amount = 0.0
        else:
            wash_sale_amount = wash_sale_amount.strip("$").replace(',', '')
            self.__wash_sale_amount = float(wash_sale_amount)

        self.__length = length

    def get_symbol(self):
        return self.__symbol

    def get_shares(self):
        return self.__shares

    def get_date_acquired(self):
        return self.__date_acquired

    def get_date_transaction(self):
        return self.__date_sold

    def get_proceeds(self):
        return self.__proceeds

    def get_cost_basis(self):
        return self.__cost_basis

    def get_cost_instruction(self):
        if self.__wash_sale_amount != 0.0:
            return "w"
        return " "

    def get_amount_adjustment(self):
        return self.__wash_sale_amount

    def get_accrued_market_discount(self):
        return self.__accrued_market_discount

    def get_gain(self):
        return self.__gain

    def get_length(self):
        return self.__length




    def __repr__(self):
        # for f8949
        #return "{0:>9.7} {1:>5} {2} {3} {4:>9.7} {5:>9.7} {6:>4} {7:>9.7} {8:>9.7}".format(self.__shares, self.__symbol, self.__date_acquired, self.__date_sold, self.__proceeds, self.__cost_basis, self.get_cost_instruction(), self.get_amount_adjustment(), float(self.__gain))
        # for 1099B test
        return "{0:>5} {1:>9.7} {2} {3} {4:>9.7} {5:>9.7} {6:>9.7} {7:>9.7} {8:>9.7}".format(self.__symbol, self.__shares, self.__date_acquired, self.__date_sold, self.__proceeds, self.__cost_basis, self.__accrued_market_discount, self.get_amount_adjustment(), float(self.__gain))

    def __str__(self):
        # for f8949
        #return "{0:>9.7} {1:>5} {2} {3} {4:>9.7} {5:>9.7} {6:>4} {7:>9.7} {8:>9.7}".format(self.__shares, self.__symbol, self.__date_acquired, self.__date_sold, self.__proceeds, self.__cost_basis, self.get_cost_instruction(), self.get_amount_adjustment(), float(self.__gain))
        # for 1099B test
        return "{0:>5} {1:>9.7} {2} {3} {4:>9.7} {5:>9.7} {6:>9.7} {7:>9.7} {8:>9.7}".format(self.__symbol, self.__shares, self.__date_acquired, self.__date_sold, self.__proceeds, self.__cost_basis, self.__accrued_market_discount, self.get_amount_adjustment(), float(self.__gain))

class Pdf2F8949:
    def __init__(self, pdf_name_list, outfile_name):
        self.__pdf_name_list = pdf_name_list
        self.__outfile_name = outfile_name
        self.__cur_symbol = ""
        self.__f8949_short_transactions = {}
        self.__f8949_covered_long_transactions = {}
        self.__f8949_noncovered_long_transactions = {}
        self.__f8949_unknown_transactions = {}
        self.__lines_per_page = 42
        self.__items_in_line = 8
        self.__table_font_size = 5
        self.__is_short = "Short"

        # 0: quantity, 1: proceeds, 2: cost basis, 3: accrued market discount, 4: wash sale, 5: gain
        self.__short_subtotals = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.__covered_long_subtotals = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.__noncovered_long_subtotals = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.__unknown_subtotals = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        self.__docx_get_cells_time = 0.0

        self.__outfile = open(self.__outfile_name, "w+")

    def read_pdf_list(self):
        self.__outfile.write("Symbol Shares DateAcquired DateSold Proceeds CostBasis AccruedMarketDiscount WashSale Gain IsShort\n")
        for pdf_file_name in self.__pdf_name_list:
            self.read_pdf(pdf_file_name)
        self.__outfile.close()

    def read_pdf(self, pdf_file_name):
        pdf = PyPDF2.PdfFileReader(pdf_file_name)
        num_pages = pdf.getNumPages()
        num = 0
        if (test_mode == False):
            num = num_pages
        else:
            num = 8
        for page in range(num):
            text = pdf.pages[page].extractText()
            textList = text.split("\n")

            self.read_page(textList)

    
    def read_page(self, textList):
        currentSymbol = ""
        shares_amount = ""
        date_acquired = ""
        date_sold = ""
        proceeds = ""
        cost_basis = ""
        accrued_market_discount = ""
        wash_sale = ""
        gain = ""
        is_short = ""
        to_see_term_length = ""
        is_basis_reported = ""

        i = 0
        while(i < len(textList)):
            if (textList[i] == "Covered Short-Term Gains or Losses on Gross Proceeds" or textList[i] == "Covered Long-Term Gains or Losses on Gross Proceeds" or textList[i] == "Noncovered Long-Term Gains or Losses on Gross Proceeds" or textList[i] == "Unknown Term Gains or Losses on Gross Proceeds"):
                to_see_term_length = textList[i]
                break
            i += 1

        if(to_see_term_length != ""):
            if(to_see_term_length[:13] == "Covered Short" or to_see_term_length[:16] == "Noncovered Short"):
                is_short = "Short"
            else:
                if(to_see_term_length[:12] == "Covered Long"):
                    is_short = "Covered Long"
                elif(to_see_term_length[:15] == "Noncovered Long"):
                    is_short = "Noncovered Long"
                elif(to_see_term_length[:7] == "Unknown"):
                    is_short = "Unknown"
                else:
                    is_short = "not a valid page"
        else:
            is_short = "not a valid page"

        if(is_short != "not a valid page"):
            i = 0
            while(textList[i] != "Box 12: "):
                i+=1
            i+=1
            if(textList[i] == "Basis Reported to the IRS"):
                is_basis_reported = "basis reported"
            elif(textList[i] == "Basis Not Reported to the IRS"):
                is_basis_reported = "basis not reported"
            else:
                is_basis_reported = "not found"

            print(is_basis_reported)

            i = 0
            #if(is_short != "Unknown" and is_short != "Noncovered Long"):
            if(is_basis_reported == "basis reported"):
                i = 0
                while(i < len(textList)):
                    if(textList[i] == "(Box 1f)"):
                        break
                    i += 1
                i += 1
                currentSymbol = textList[i]
            else:
                i = 0
                while(i < len(textList)):
                    if(textList[i] == "Discount"):
                        break
                    i += 1
                i += 1
                currentSymbol = textList[i]
            while(i < len(textList)):
                # if not info needed, pass
                while( not(is_valid_num(textList[i]))): 
                    i += 1
            
                date_acquired = textList[i]
                i += 1
                proceeds = textList[i]
                i += 1
                cost_basis = textList[i]
                i += 1
                date_sold = textList[i]
                i += 1
                if(textList[i] == "Subtotals"):
                    i += 3
                    if(not(is_valid_num(textList[i]))):
                        currentSymbol = textList[i]
                        while( not(is_valid_num(textList[i])) and textList[i][:7] != "THIS IS"):
                            i += 1
                    else:
                        while(1):
                            if(textList[i][:7] == "THIS IS"):
                                break
                            i += 1
                else:
                    shares_amount = textList[i]
                    i += 1
                    wash_sale = textList[i]
                    i += 1
                    # for the additional notes. ignore any additional notes
                    if(not(is_valid_num(textList[i]))):
                        i += 1
                    gain = textList[i]
                    i += 1
                    accrued_market_discount = textList[i]
                    i += 1

                    #print(currentSymbol + " " + shares_amount + " " +  date_acquired + " " + date_sold + " " + proceeds + " " + cost_basis + " " + accrued_market_discount + " " + wash_sale + " " + gain + " " + is_short + "\n")
                    self.__outfile.write(currentSymbol + " " + shares_amount + " " +  date_acquired + " " + date_sold + " " + proceeds + " " + cost_basis + " " + accrued_market_discount + " " + wash_sale + " " + gain + " " + is_short + "\n")
                    
                    transaction = Transaction(currentSymbol, shares_amount, date_acquired, date_sold, proceeds, cost_basis, accrued_market_discount, wash_sale, gain, is_short)

                    if transaction.get_length() == "Short":
                        transaction_list = self.__f8949_short_transactions.get(transaction.get_symbol())
                        if transaction_list == None:
                            transaction_list = []
                            transaction_list.append(transaction)
                            self.__f8949_short_transactions[transaction.get_symbol()] = transaction_list 
                        else:
                            transaction_list.append(transaction)

                        # 0: quantity, 1: proceeds, 2: cost basis, 3: accrued market discount, 4: wash sale, 5: gain
                        self.__short_subtotals[0] += 1
                        self.__short_subtotals[1] += transaction.get_proceeds()
                        self.__short_subtotals[2] += transaction.get_cost_basis()
                        self.__short_subtotals[3] += transaction.get_accrued_market_discount()
                        self.__short_subtotals[4] += transaction.get_amount_adjustment() # used to get wash sale
                        self.__short_subtotals[5] += transaction.get_gain()

                    elif transaction.get_length() == "Covered Long":
                        transaction_list = self.__f8949_covered_long_transactions.get(transaction.get_symbol())
                        if transaction_list == None:
                            transaction_list = []
                            transaction_list.append(transaction)
                            self.__f8949_covered_long_transactions[transaction.get_symbol()] = transaction_list
                        else:
                            transaction_list.append(transaction)

                        # 0: quantity, 1: proceeds, 2: cost basis, 3: accrued market discount, 4: wash sale, 5: gain
                        self.__covered_long_subtotals[0] += 1
                        self.__covered_long_subtotals[1] += transaction.get_proceeds()
                        self.__covered_long_subtotals[2] += transaction.get_cost_basis()
                        self.__covered_long_subtotals[3] += transaction.get_accrued_market_discount()
                        self.__covered_long_subtotals[4] += transaction.get_amount_adjustment() # used to get wash sale
                        self.__covered_long_subtotals[5] += transaction.get_gain()
                    
                    elif transaction.get_length() == "Noncovered Long":
                        transaction_list = self.__f8949_noncovered_long_transactions.get(transaction.get_symbol())
                        if transaction_list == None:
                            transaction_list = []
                            transaction_list.append(transaction)
                            self.__f8949_noncovered_long_transactions[transaction.get_symbol()] = transaction_list
                        else:
                            transaction_list.append(transaction)

                        # 0: quantity, 1: proceeds, 2: cost basis, 3: accrued market discount, 4: wash sale, 5: gain
                        self.__noncovered_long_subtotals[0] += 1
                        self.__noncovered_long_subtotals[1] += transaction.get_proceeds()
                        self.__noncovered_long_subtotals[2] += transaction.get_cost_basis()
                        self.__noncovered_long_subtotals[3] += transaction.get_accrued_market_discount()
                        self.__noncovered_long_subtotals[4] += transaction.get_amount_adjustment() # used to get wash sale
                        self.__noncovered_long_subtotals[5] += transaction.get_gain()

                    elif transaction.get_length() == "Unknown":
                        transaction_list = self.__f8949_unknown_transactions.get(transaction.get_symbol())
                        if transaction_list == None:
                            transaction_list = []
                            transaction_list.append(transaction)
                            self.__f8949_unknown_transactions[transaction.get_symbol()] = transaction_list
                        else:
                            transaction_list.append(transaction)

                        # 0: quantity, 1: proceeds, 2: cost basis, 3: accrued market discount, 4: wash sale, 5: gain
                        self.__unknown_subtotals[0] += 1
                        self.__unknown_subtotals[1] += transaction.get_proceeds()
                        self.__unknown_subtotals[2] += transaction.get_cost_basis()
                        self.__unknown_subtotals[3] += transaction.get_accrued_market_discount()
                        self.__unknown_subtotals[4] += transaction.get_amount_adjustment() # used to get wash sale
                        self.__unknown_subtotals[5] += transaction.get_gain()


                # break when reach "THIS IS YOUR BLAH BLAH BLAH"
                if(textList[i][:7] == "THIS IS"):
                    break

    def print_short_subtotals(self):
        for i in self.__short_subtotals:
            print(str(i) + ", "),
        print("\n")
    
    def print_covered_long_subtotals(self):
        for i in self.__covered_long_subtotals:
            print(str(i) + ", "),
        print("\n")

    def print_noncovered_long_subtotals(self):
        for i in self.__noncovered_long_subtotals:
            print(str(i) + ", "),
        print("\n")

    def print_unknown_subtotals(self):
        for i in self.__unknown_subtotals:
            print(str(i) + ", "),
        print("\n")

    def print_test(self):
        for symbol in self.__f8949_short_transactions:
            print(symbol)
            transaction_list = self.__f8949_covered_long_transactions.get(symbol)
            print("what")
            if(transaction_list != None):
                for transaction in transaction_list:
                    print(transaction.get_symbol() + " " + str(transaction.get_shares()))

    def short_transactions_pdf(self, name, taxpayer_id, year):
        self.text_to_pdf("Short", name, taxpayer_id, year)

    def covered_long_transactions_pdf(self, name, taxpayer_id, year):
        self.text_to_pdf("Covered Long", name, taxpayer_id, year)

    def noncovered_long_transactions_pdf(self, name, taxpayer_id, year):
        self.text_to_pdf("Noncovered Long", name, taxpayer_id, year)

    def unknown_transactions_pdf(self, name, taxpayer_id, year):
        self.text_to_pdf("Unknown", name, taxpayer_id, year)


    def text_to_pdf(self, length, name, taxpayer_id, year):


        if(length == "Short"):
            transaction_set = self.__f8949_short_transactions
        elif(length == "Covered Long"):
            transaction_set = self.__f8949_covered_long_transactions
        elif(length == "Noncovered Long"):
            transaction_set = self.__f8949_noncovered_long_transactions
        elif(length == "Unknown"):
            transaction_set = self.__f8949_unknown_transactions

        pdf = FPDF(format = 'letter', unit = 'in')
        pdf.set_font("Times", '', 10.0)

        # finding the effective page width or epw for short
        epw = pdf.w - 2*pdf.l_margin

        i = 0
        for symbol in transaction_set:
            transaction_list = transaction_set.get(symbol)
            #if(transaction_list != None):
            for transaction in transaction_list:
                if (i == 0):
                    # for a new page
                    pdf.add_page()
                    # header thing
                    pdf.set_font("Times", '', 10.0)

                    pdf.cell(epw/8, 1.0, 'Statement A', border = "LRT", ln = 0, align = 'C')
                    pdf.set_font('Times', 'B', 14.0)
                    pdf.cell(epw*6/8, 0.5, 'Sales and Other Dispositions of Capital Assets', border = "LRT", ln = 2, align = 'C')
                    curr_x = pdf.get_x()
                    curr_y = pdf.get_y()
                    pdf.set_font('Times', '', 10.0)
                    pdf.cell(epw*6/8, 0.5, length + "-term transactions reported on Form 1099-B with basis reported to the IRS", border = "LRB", align = 'C')
                    pdf.set_xy(curr_x + epw*6/8, curr_y - 0.5)
                    pdf.cell(epw/8, 1.0, year, border = "LRT", ln = 1, align = 'C')

                    # personal info
                    pdf.set_font('Times', '', 8.0)
                    pdf.cell(epw*2/3, 0.25, 'Name(s) shown on return', border = "LRT", ln = 0, align = 'L')
                    pdf.cell(epw/3, 0.25, 'Taxpayer Identification No.', border = "LRT", ln = 1, align = 'L')
                    pdf.set_font('Times', '', 10.0)
                    pdf.cell(epw*2/3, 0.25, '   ' + name, border = "LRB", ln = 0, align = 'L')
                    pdf.cell(epw/3, 0.25, taxpayer_id, border = "LRB", ln = 1, align = 'C')

                    # column names
                    pdf.set_font('Times', '', 6.5)

                    curr_x = pdf.get_x()
                    curr_y = pdf.get_y()
                    pdf.multi_cell(epw*3/10, 1.0/6, '(a)\nDescription of property\n(Example: 100 sh. XYZ Co.)\n \n \n ', border = 1, align = 'C')

                    pdf.set_xy(curr_x + epw*3/10, curr_y)
                    curr_x = pdf.get_x()
                    curr_y = pdf.get_y()
                    pdf.multi_cell(epw/10, 1.0/5, '(b)\nDate acquired\n(Mo., day, yr.)\n(MM/DD/YYYY)\n ', border = 1, align = 'C')

                    pdf.set_xy(curr_x + epw/10, curr_y)
                    curr_x = pdf.get_x()
                    curr_y = pdf.get_y()
                    pdf.multi_cell(epw/10, 1.0/5, '(c)\nDate sold\n(Mo., day, yr.)\n(MM/DD/YYYY)\n ', border = 1, align = 'C')

                    pdf.set_xy(curr_x + epw/10, curr_y)
                    curr_x = pdf.get_x()
                    curr_y = pdf.get_y()
                    pdf.multi_cell(epw/10, 1.0/5, '(d)\nProceeds\n(sale price)\n \n ', border = 1, align = 'C')

                    pdf.set_xy(curr_x + epw/10, curr_y)
                    curr_x = pdf.get_x()
                    curr_y = pdf.get_y()
                    pdf.multi_cell(epw/10, 1.0/5, '(e)\nCost or other basis\n \n \n ', border = 1, align = 'C')

                    pdf.set_xy(curr_x + epw/10, curr_y)
                    curr_x = pdf.get_x()
                    curr_y = pdf.get_y()
                    pdf.multi_cell(epw*1.6/10, 0.5/3, 'Adjustment, if any,\nto gain or loss\n ', border = 1, align = 'C')

                    pdf.set_xy(curr_x, curr_y + 0.5)
                    temp_curr_x = pdf.get_x()
                    temp_curr_y = pdf.get_y()
                    pdf.multi_cell(epw*0.6/10, 0.5/3, '(f)\nCode(s)\n ', border = 1, align = 'C')

                    pdf.set_xy(temp_curr_x + epw*0.6/10, temp_curr_y)
                    temp_curr_x = pdf.get_x()
                    temp_curr_y = pdf.get_y()
                    pdf.multi_cell(epw/10, 0.5/3, '(g)\nAmount of\nadjustment', border = 1, align = 'C')

                    pdf.set_xy(curr_x + epw*1.6/10, curr_y)
                    pdf.multi_cell(epw*1.4/10, 1.0/6, '(h)\nGain or (loss)\n Subtract column (e)\nfrom column (d) and\ncombine the result\nwith column (g)', border = 1, align = 'C')

                # data
                pdf.set_font('Times', '', 8.0)
                # text height will be the same as font size
                th = pdf.font_size

                curr_x = pdf.get_x()
                curr_y = pdf.get_y()
                pdf.multi_cell(epw*3/10, th, stringify_no_round(transaction.get_shares()) + " sh.\n" + transaction.get_symbol(), border = 1, align = 'L')
                pdf.set_xy(curr_x + epw*3/10, curr_y)
                pdf.cell(epw/10, th*2, str(transaction.get_date_acquired()), border = 1, ln = 0, align = 'C')
                pdf.cell(epw/10, th*2, str(transaction.get_date_transaction()), border = 1, ln = 0, align = 'C')
                pdf.cell(epw/10, th*2, stringify_two_decimals(transaction.get_proceeds()), border = 1, ln = 0, align = 'C')
                pdf.cell(epw/10, th*2, stringify_two_decimals(transaction.get_cost_basis()), border = 1, ln = 0, align = 'C')
                pdf.cell(epw*0.6/10, th*2, str(transaction.get_cost_instruction()), border = 1, ln = 0, align = 'C')
                if(transaction.get_amount_adjustment() != 0.0):
                    pdf.cell(epw/10, th*2, stringify_two_decimals(transaction.get_amount_adjustment()), border = 1, ln = 0, align = 'C')
                else:
                    pdf.cell(epw/10, th*2, ' ', border = 1, ln = 0, align = 'C')
                pdf.cell(epw*1.4/10, th*2, stringify_two_decimals(transaction.get_gain()), border = 1, ln = 1, align = 'C')

                i += 1
                # we will have new page every 32 entries
                if(i == 32):
                    i = 0


        pdf.output(length + "_transactions_" + "results_from_pdf.pdf", 'F')

class Csv2F8949:
    def __init__(self, csv_name_list, outfile_name):
        self.__csv_name_list = csv_name_list
        self.__outfile_name = outfile_name
        self.__cur_symbol = ""
        self.__f8949_short_transactions = {}
        self.__f8949_long_transactions = {}
        self.__lines_per_page = 42
        self.__items_in_line = 8
        self.__table_font_size = 5

        self.__docx_get_cells_time = 0.0

    def read_csv_list(self):
        for csv_file_name in self.__csv_name_list:
            self.read_csv(csv_file_name)

    def read_csv(self, csv_file_name):
        with open(csv_file_name, 'rb') as csvfile:
            #csv_reader = csv.reader(csvfile, delimiter = ' ', quotechar = '|')
            csv_reader = csv.reader(csvfile, skipinitialspace=True, delimiter = ',', quoting=csv.QUOTE_NONE)
            for row in csv_reader:
                #print(row)
                #print(', '.join(row))
                
                if len(row) == 0:
                    continue
                elif row[0] == "Sell" or row[0] == "Buy To Cover":
                    #symbol, 1num_share, 2purchase_date, 4cost_basis, 5transaction_date, 7sales_price, 8gain, 9wash_sale_amount, 10period
                    #print(self.__cur_symbol, row[1], row[2], row[4], row[5], row[7], row[8], row[9], row[10])
                    #symbol, 1shares, 2date_acquired, 5date_sold, 7proceeds, 4cost_basis, accrued_market_discount, 9wash_sale_amount, 8gain, 10length
                    transaction = Transaction(self.__cur_symbol, row[1], row[2], row[5], row[7], row[4], "--", row[9], row[8], row[10])
                    if row[10]=="Short":
                        #self.__f8949_short_transactions.append(transaction)
                        transaction_list = self.__f8949_short_transactions.get(self.__cur_symbol)
                        if transaction_list == None:
                           transaction_list = []
                           transaction_list.append(transaction)
                           self.__f8949_short_transactions[self.__cur_symbol] = transaction_list
                        else:
                           transaction_list.append(transaction)
                    else:
                        #self.__f8949_long_transactions.append(transaction)
                        transaction_list = self.__f8949_long_transactions.get(self.__cur_symbol)
                        if transaction_list == None:
                           transaction_list = []
                           transaction_list.append(transaction)
                           self.__f8949_long_transactions[self.__cur_symbol] = transaction_list
                        else:
                           transaction_list.append(transaction)
                elif row[0][0] == '#':
                    continue 
                else:
                    self.__cur_symbol = row[0]


    def short_transactions_pdf(self, name, taxpayer_id, year):
        self.text_to_pdf("Short", name, taxpayer_id, year)

    def long_transactions_pdf(self, name, taxpayer_id, year):
        self.text_to_pdf("Long", name, taxpayer_id, year)
    """
    def noncovered_long_transactions_pdf(self, name, taxpayer_id, year):
        self.text_to_pdf("Noncovered Long", name, taxpayer_id, year)

    def unknown_transactions_pdf(self, name, taxpayer_id, year):
        self.text_to_pdf("Unknown", name, taxpayer_id, year)
    """

    def text_to_pdf(self, length, name, taxpayer_id, year):


        if(length == "Short"):
            transaction_set = self.__f8949_short_transactions
        elif(length == "Long"):
            transaction_set = self.__f8949_long_transactions
        """
        elif(length == "Noncovered Long"):
            transaction_set = self.__f8949_noncovered_long_transactions
        elif(length == "Unknown"):
            transaction_set = self.__f8949_unknown_transactions
        """
        pdf = FPDF(format = 'letter', unit = 'in')
        pdf.set_font("Times", '', 10.0)

        # finding the effective page width or epw for short
        epw = pdf.w - 2*pdf.l_margin

        i = 0
        for symbol in transaction_set:
            transaction_list = transaction_set.get(symbol)
            #if(transaction_list != None):
            for transaction in transaction_list:
                if (i == 0):
                    # for a new page
                    pdf.add_page()
                    # header thing
                    pdf.set_font("Times", '', 10.0)

                    pdf.cell(epw/8, 1.0, 'Statement A', border = "LRT", ln = 0, align = 'C')
                    pdf.set_font('Times', 'B', 14.0)
                    pdf.cell(epw*6/8, 0.5, 'Sales and Other Dispositions of Capital Assets', border = "LRT", ln = 2, align = 'C')
                    curr_x = pdf.get_x()
                    curr_y = pdf.get_y()
                    pdf.set_font('Times', '', 10.0)
                    pdf.cell(epw*6/8, 0.5, length + "-term transactions reported on Form 1099-B with basis reported to the IRS", border = "LRB", align = 'C')
                    pdf.set_xy(curr_x + epw*6/8, curr_y - 0.5)
                    pdf.cell(epw/8, 1.0, year, border = "LRT", ln = 1, align = 'C')

                    # personal info
                    pdf.set_font('Times', '', 8.0)
                    pdf.cell(epw*2/3, 0.25, 'Name(s) shown on return', border = "LRT", ln = 0, align = 'L')
                    pdf.cell(epw/3, 0.25, 'Taxpayer Identification No.', border = "LRT", ln = 1, align = 'L')
                    pdf.set_font('Times', '', 10.0)
                    pdf.cell(epw*2/3, 0.25, '   ' + name, border = "LRB", ln = 0, align = 'L')
                    pdf.cell(epw/3, 0.25, taxpayer_id, border = "LRB", ln = 1, align = 'C')

                    # column names
                    pdf.set_font('Times', '', 6.5)

                    curr_x = pdf.get_x()
                    curr_y = pdf.get_y()
                    pdf.multi_cell(epw*3/10, 1.0/6, '(a)\nDescription of property\n(Example: 100 sh. XYZ Co.)\n \n \n ', border = 1, align = 'C')

                    pdf.set_xy(curr_x + epw*3/10, curr_y)
                    curr_x = pdf.get_x()
                    curr_y = pdf.get_y()
                    pdf.multi_cell(epw/10, 1.0/5, '(b)\nDate acquired\n(Mo., day, yr.)\n(MM/DD/YYYY)\n ', border = 1, align = 'C')

                    pdf.set_xy(curr_x + epw/10, curr_y)
                    curr_x = pdf.get_x()
                    curr_y = pdf.get_y()
                    pdf.multi_cell(epw/10, 1.0/5, '(c)\nDate sold\n(Mo., day, yr.)\n(MM/DD/YYYY)\n ', border = 1, align = 'C')

                    pdf.set_xy(curr_x + epw/10, curr_y)
                    curr_x = pdf.get_x()
                    curr_y = pdf.get_y()
                    pdf.multi_cell(epw/10, 1.0/5, '(d)\nProceeds\n(sale price)\n \n ', border = 1, align = 'C')

                    pdf.set_xy(curr_x + epw/10, curr_y)
                    curr_x = pdf.get_x()
                    curr_y = pdf.get_y()
                    pdf.multi_cell(epw/10, 1.0/5, '(e)\nCost or other basis\n \n \n ', border = 1, align = 'C')

                    pdf.set_xy(curr_x + epw/10, curr_y)
                    curr_x = pdf.get_x()
                    curr_y = pdf.get_y()
                    pdf.multi_cell(epw*1.6/10, 0.5/3, 'Adjustment, if any,\nto gain or loss\n ', border = 1, align = 'C')

                    pdf.set_xy(curr_x, curr_y + 0.5)
                    temp_curr_x = pdf.get_x()
                    temp_curr_y = pdf.get_y()
                    pdf.multi_cell(epw*0.6/10, 0.5/3, '(f)\nCode(s)\n ', border = 1, align = 'C')

                    pdf.set_xy(temp_curr_x + epw*0.6/10, temp_curr_y)
                    temp_curr_x = pdf.get_x()
                    temp_curr_y = pdf.get_y()
                    pdf.multi_cell(epw/10, 0.5/3, '(g)\nAmount of\nadjustment', border = 1, align = 'C')

                    pdf.set_xy(curr_x + epw*1.6/10, curr_y)
                    pdf.multi_cell(epw*1.4/10, 1.0/6, '(h)\nGain or (loss)\n Subtract column (e)\nfrom column (d) and\ncombine the result\nwith column (g)', border = 1, align = 'C')

                # data
                pdf.set_font('Times', '', 8.0)
                # text height will be the same as font size
                th = pdf.font_size

                curr_x = pdf.get_x()
                curr_y = pdf.get_y()
                pdf.multi_cell(epw*3/10, th, stringify_no_round(transaction.get_shares()) + " sh.\n" + transaction.get_symbol(), border = 1, align = 'L')
                pdf.set_xy(curr_x + epw*3/10, curr_y)
                pdf.cell(epw/10, th*2, str(transaction.get_date_acquired()), border = 1, ln = 0, align = 'C')
                pdf.cell(epw/10, th*2, str(transaction.get_date_transaction()), border = 1, ln = 0, align = 'C')
                pdf.cell(epw/10, th*2, stringify_two_decimals(transaction.get_proceeds()), border = 1, ln = 0, align = 'C')
                pdf.cell(epw/10, th*2, stringify_two_decimals(transaction.get_cost_basis()), border = 1, ln = 0, align = 'C')
                pdf.cell(epw*0.6/10, th*2, str(transaction.get_cost_instruction()), border = 1, ln = 0, align = 'C')
                if(transaction.get_amount_adjustment() != 0.0):
                    pdf.cell(epw/10, th*2, stringify_two_decimals(transaction.get_amount_adjustment()), border = 1, ln = 0, align = 'C')
                else:
                    pdf.cell(epw/10, th*2, ' ', border = 1, ln = 0, align = 'C')
                pdf.cell(epw*1.4/10, th*2, stringify_two_decimals(transaction.get_gain()), border = 1, ln = 1, align = 'C')

                i += 1
                # we will have new page every 32 entries
                if(i == 32):
                    i = 0


        pdf.output(length + "_transactions_" + "results_from_csv.pdf", 'F')



if __name__ == "__main__":

    pdf_or_csv = int(raw_input("Will you input pdf or csv files? Type 0 for pdf and 1 for csv: "))
    if(pdf_or_csv == 0):
        print("pdf")
    else:
        print("csv")
    person_name = raw_input("Enter Full Name: ")
    print(person_name)
    id_number = raw_input("Enter Taxpayer Identification Number: ")
    print(id_number)
    year = raw_input("Enter Year: ")
    print(year)
    amount = int(raw_input("How many files: "))
    print(amount)

    file_inputs_list = []

    for i in range(0, amount) :
        file_input_name = raw_input("Enter file name: ")
        file_inputs_list.append(file_input_name)

    print(file_inputs_list)


    if(pdf_or_csv == 0):

        start_time = time.time()   
        pdf_reader = Pdf2F8949(file_inputs_list, "result_file.txt")

        print("---- %s seconds for generating object" % (time.time() - start_time))

        start_time = time.time()   
        pdf_reader.read_pdf_list()
        print("---- %s seconds for reading pdf file" % (time.time() - start_time))

        print("Short subtotals: "),
        pdf_reader.print_short_subtotals()
        print("Covered Long subtotals: "),
        pdf_reader.print_covered_long_subtotals()
        print("Noncovered Long subtotals: "),
        pdf_reader.print_noncovered_long_subtotals()
        print("Unknown subtotals: "),
        pdf_reader.print_unknown_subtotals()

        # text to pdfs
        pdf_reader.short_transactions_pdf(person_name, id_number, year)
        pdf_reader.covered_long_transactions_pdf(person_name, id_number, year)
        pdf_reader.noncovered_long_transactions_pdf(person_name, id_number, year)
        pdf_reader.unknown_transactions_pdf(person_name, id_number, year)

    else:
        start_time = time.time()   
        csv_reader = Csv2F8949(file_inputs_list, "result_file")
        print("---- %s seconds for generating object" % (time.time() - start_time))

        start_time = time.time()   
        csv_reader.read_csv_list()
        print("---- %s seconds for reading csv file" % (time.time() - start_time))

        csv_reader.short_transactions_pdf(person_name, id_number, year)
        csv_reader.long_transactions_pdf(person_name, id_number, year)



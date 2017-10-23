import subprocess
import io
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
import re
import unicodedata

"""
Converts a given filename from a a pdf to a string using PDFMiner
and returns outputted text. PDFMiner can unfortunately be quite slow,
but is the best solution for now to read in row names.
@param fname: Filename
@param pages: Pages to convert
return: converted text
"""
def convert(fname, pages=None):
    if not pages:
        pagenums = set()
    else:
        pagenums = set(pages)

    output = io.StringIO()
    manager = PDFResourceManager()
    converter = TextConverter(manager, output, laparams=LAParams())
    interpreter = PDFPageInterpreter(manager, converter)

    infile = open(fname, 'rb')
    for page in PDFPage.get_pages(infile, pagenums):
        interpreter.process_page(page)
    #print([method_name for method_name in dir(output) if callable(getattr(output, method_name))])

    infile.close()
    converter.close()
    text = output.getvalue()
    output.close()
    return text 

"""
Returns a list of row names on a given page of a pdf.
@param string: Converted PDF text. Use PDFMiner to convert this text.
return: List of row names
"""
def return_row_names(string):
	found = re.search("COST(.+?)Prior",string, flags=re.DOTALL)
	group = found.group(1)
	rows = group.split("\n")
	rows = rows[1:]
	#for i in range(0,rows.length()):
	# for i in range(0,len(rows)):
	# 	if "Quantity" in rows[i]:
	# 		if rows[i-1][0] != '6':
	# 			rows[i-2:i-1] = [''.join(rows[i-2:i-1])]


	rows = [row for row in rows if row != ""]
	return rows

"""
Generates a list of names for columns in the table.
Utility funciton for parse_table_string().
@param: year used to determine column names.
return: list of columns
"""
def generate_col_names(year):
	col_list = ["Prior Years"]
	for i in range(year-2, year+5):
		s = "FY " + str(i)
		if i == year:
			for j in range(0,3):
				if j == 0: 
					col_list.append(s + " Base")
				elif j == 1: 
					col_list.append(s + " OCO")
				elif j == 2:
					col_list.append(s + " Total")
		else:
			col_list.append(s)
	col_list.append("Cost To Complete")
	col_list.append("Total Cost")
	return col_list

"""
Parses a given string returned from a regular expression corresponding with values in a table row.
Use pdftotxt Linux utility converted text for this function.
@param string: String needed to parse
@param year: param needed for generate_col_names()
return: dictionary of cell values corresponding with column names for a given row.
"""
def parse_table_string(string,year):
	string = " ".join(string.split()) #Remove extra whitespace in string
	cell_array = string.split()
	for s in cell_array:
		# if u'\xao' in s:
			#s = s.replace(u'\xao',u'')
		new_str = unicodedata.normalize("NFKD", s) #normalize string
	col_list = generate_col_names(year)
	#table_dict = {cell, col_name for cell, col_name in cell_array, col_list}
	dictionary = dict(zip(col_list, cell_array)) 
	return dictionary


"""
Extracts table information using a given PDF page text. For every row present, regular expression
is used to extract row information. This information is stored as a string and then parsed to produce
a dictionary. Finally, this dictionary is placed into a dictionary containing with a key that matches the
row name.
@param rows: List of row names to extract from
@param text: Converted PDF text (string)
@param year: year of converted PDF (should be in PDF filename, for example, 'AFD-150309-012.pdf' would be year=2016))
return: extracted table information as a dictionary. Dictionary can be used to be placed in JSON format.
"""
def extract_table(rows,text,year=2018): 
	a = ""
	table_dict = {}
	try: 
		for i in range(0,len(rows)):
			#print(rows[i])
			if '(' in rows[i]: # If an open parentheses is present in string, re won't accept this. Must get rid of parentheses.
				index = rows[i].index('(')
				#rows[i] = rows[i][0:index] + '/' + rows[i][index:]
				string = rows[i][index+1:]
				index2 = rows[i+1].index(')')
				string_2nd = rows[i+1][:index2-1]
				found = re.search(string + '(.+?)' + string_2nd,text,flags=re.DOTALL)
				a += found.group(1)
				a += "\n"
				dictionary = parse_table_string(found.group(1),year)
				print(dictionary)
				table_dict[rows[i] + rows[i+1]] = (dictionary)
				#print(table_dict)
				#print(found.group(1))
			elif ')' in rows[i]: #If close parentheses is present, string not needed. Continue.
				continue
			elif i == len(rows)-1: #If i is last string, then find data all the way up to divider A. 
				found = re.search(rows[i] + '(.+?)A.', text, flags = re.DOTALL)
				a += found.group(1)
				a += "\n"
				dictionary = parse_table_string(found.group(1),year)
				print(dictionary)
				table_dict[rows[i]] = (dictionary)
				#print(table_dict)
				#print(found.group(1))
				break
			else:	
				if (i < len(rows)-1):
					if (i > 0 and rows[i-1][0] == '6' and rows[i][0] != '6' and rows[i+1][0] == '6') or (i > 0 and i < len(rows)-2 and rows[i-1][0] == '6' and rows[i][0] != '6' and rows[i+1][0] != '6' and rows[i+2][0] == '6'):
						print("HI")
						continue #Hacky
					elif i > 1 and i < len(rows)-2 and rows[i-2][0] == '6' and rows[i-1][0] != '6' and rows[i][0] != '6':
						continue
					string_2nd = rows[i+1]
					key_string = ''
					if '(' in rows[i+1]: #row has open parentheses, search past open parentheses
						index = rows[i+1].index('(')
						string_2nd = rows[i+1][:index-1]
					count = i + 1
					while ((count < len(rows)-1) and rows[count][0] != '6'):
						key_string = key_string + " " + rows[count]
						count = count + 1
					found = re.search(rows[i] + '(.+?)' + string_2nd,text, flags=re.DOTALL)
					a += found.group(1)
					# table_dict[rows[i] + key_string] = found.group(1)
					a += "\n"
					dictionary = parse_table_string(found.group(1),year)
					print(dictionary)
					table_dict[rows[i] + key_string] = dictionary
					#print(table_dict)
					#print(parse_table_string(found.group(1),year))
					#print(found.group(1))
	except Exception as e:
		print(e)
		print("Table could not be parsed.")

	print("TEST" + str(table_dict))
	return a, table_dict



"""
Writes a given page's text to a an output file. This file can later be read from and stored as JSON.
@param page1: page to start reading PDF from
@param page2: page to end reading PDF from
@param filename: filename of PDF to convert
"""
def write_page_text(page1, page2,filename=''):

	# text = convert('afd2018.pdf', pages=[344])
	with open('newfile.txt', 'w') as workfile:
		for i in range(page1,page2):
			text = convert(filename, pages=[i])
			try: 
				rows = return_row_names(text)
			except Exception as e:
				print("No table")
				continue
		# AFD-150309-012.pdf
			# subprocess.call(['pdftotext','afd2018.pdf','o.txt','-layout','-f','345','-l','345'])
			subprocess.call(['pdftotext',filename,'o.txt','-layout','-f',str(i + 1),'-l',str(i + 1)])
			data = ''
			with open('o.txt', 'r') as myfile:
		   		data=myfile.read().replace('\n', '')
			s, table_dict = extract_table(rows,data,year=2016)
			#print('HIIII' + s)
			#print(table_dict)
			workfile.write(str(table_dict))
			workfile.write('\n')
		workfile.close()


#print(generate_col_names(2018))
#print
write_page_text(70,71,filename='AFD-150309-012.pdf')

# print(text)
# print(repr(text))


# print(repr(data))







# print(data)

# print(repr(data))

# found = re.search('Program Element \(Number/Name\)(.+?)Date',data, flags=re.DOTALL).group(1)
# print(found)

# found = re.search('Appropriation/Budget Activity(.+?)UNCLASSIFIED',dataN, flags=re.DOTALL).group(1)
# print(found)

# found = re.search('Total Program Element(.+?)675',data, flags=re.DOTALL)


# string = found.group(1)

# print("/n")

# string.replace(")","")
# string.replace("(","")

# found = re.search(string + '(.+?)Q', data, flags=re.DOTALL)

# string = found.group(1)



# found = re.search('Quantity of RDT&E Articles' + '(.+?)Note', data, flags=re.DOTALL)


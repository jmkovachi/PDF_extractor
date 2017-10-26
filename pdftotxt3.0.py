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
	found = re.search("Total\nCost(.+?)A\.",string,flags=re.DOTALL)
	group = found.group(1)
	group = group.split("\n")
	rows = []
	#print(group)
	for i in range(len(group)):
		# print(group[i])
		if "Total Program Element" in group[i]:
			rows.append(group[i])
			continue
		if "Quantity" in group[i]:
			rows.append(group[i])
			continue
		try:
			f = re.search("6(.+?):", group[i], flags=re.DOTALL).group(1)

			s = ''
			#rows.append(group[i])
			count = i
			while (count < len(group)-1 and group[count] != ''):
				s += group[count] + "\n"
				count = count + 1
			if count != i:
				s = s[:-1]
			rows.append(s)
		except Exception as e:
			continue

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
			# print(rows)
			search_string = ''
			search_2ndstring = ''
			if "\n" in rows[i]:
				index = rows[i].index('\n')
				search_string = rows[i][:index].replace("\n","")
				search_2ndstring = rows[i][index:].replace("\n","")			
			elif i == len(rows)-1:
				search_string = rows[i]
				search_2ndstring = 'A.'
				found = re.search(re.escape(search_string) + '(.+?)' + ('A\.|Note'), text, flags = re.DOTALL)
				dictionary = parse_table_string(found.group(1),year)
				table_dict[rows[i]] = dictionary
				continue #Do not want to exit loop here- re.escape messes up A.|Note
			else:
				search_string = rows[i]
				search_2ndstring = rows[i+1]
				if '\n' in rows[i+1]:
					index = rows[i+1].index('\n')
					search_2ndstring = rows[i+1][:index].replace("\n","")
				
			found = re.search(re.escape(search_string) + '(.+?)' + re.escape(search_2ndstring), text, flags=re.DOTALL)
			dictionary = parse_table_string(found.group(1),year)
			table_dict[rows[i].replace('\n',' ')] = dictionary

	except Exception as e:
		print(e)
		print("Table could not be parsed.")
	return a, table_dict

def search_for_desc(desc):
	found = re.search('A. Mission Description and Budget Item Justification(.+?)(PE 0|B. Program|B. Accomplishments)', desc, re.DOTALL)
	return found.group(1)


def parse_year_from_filename(filename):
	subprocess.call(['pdftotext',filename,'o2.txt','-f','1','-l','1'])
	data2 = ''
	with open('o2.txt', 'r') as myfile:
			data2=myfile.read()
	found = re.search('Fiscal Year \(FY\) (....)',data2, re.DOTALL)
	return int(found.group(1))

def return_data(page1, page2, filename):
	subprocess.call(['pdftotext',filename,'o2.txt','-layout','-f',str(page1 + 1),'-l',str(page2 + 1)])
	data2 = ''
	with open('o2.txt', 'r') as myfile:
		data2=myfile.read()
	return data2

def return_R2_metadata(data):
	found = re.search('\(Number/Name\)\s(.+?)(PE.+?)Prior',data, re.DOTALL)
	appropriation = found.group(1).strip()
	program_element = found.group(2)
	if '\n' in program_element:
		appropriation += ' ' + program_element.split('\n')[1]
		program_element = program_element.split('\n')[0]
	return appropriation, program_element

"""
Writes a given page's text to a an output file. This file can later be read from and stored as JSON.
@param page1: page to start reading PDF from
@param page2: page to end reading PDF from
@param filename: filename of PDF to convert
"""
def write_page_text(page1, page2,filename=''):
	with open('newfile.txt', 'w') as workfile:
		set = False #bool to help decide which pages should be searched
		count = 0
		for i in range(page1,page2):
			if (set):
				count += 1
				set = False
				try:
					subprocess.call(['pdftotext',filename,'o2.txt','-f',str(i + 1),'-l',str(i + 1)]) 
					data2 = ''
					with open('o2.txt', 'r') as myfile:
			   			data2=myfile.read()

					rows = return_row_names(data2)
				except Exception as e:
					print(e)
					print("No table")
					continue

				subprocess.call(['pdftotext',filename,'o.txt','-layout','-f',str(i + 1),'-l',str(i + 1)]) #this could possibly be improved (don't need to call twice)
				data = ''
				with open('o.txt', 'r') as myfile:
			   		data=myfile.read().replace('\n', '')

				s, table_dict = extract_table(rows,data,year=parse_year_from_filename(filename))
				
				try: 
					table_dict['A. Mission Description and Budget Item Justification'] = search_for_desc(data)
					appropriation, program_element = return_R2_metadata(return_data(i,i,filename))
					table_dict['Appropriation/Budget Activity'] = appropriation
					table_dict['R-1 Program Element (Number/Name)'] = program_element
				except Exception as e:
					print(e)
					print("cannot extract desc")

				workfile.write(str(table_dict))
				workfile.write('\n')
			else:
				subprocess.call(['pdftotext',filename,'o2.txt','-f',str(i + 1),'-l',str(i + 1)])
				data2 = ''
				with open('o2.txt', 'r') as myfile:
			   			data2=myfile.read()

				try: 
					found = re.search('THIS PAGE(.+?)LEFT BLANK', data2, re.DOTALL)
					found.group(1) #Will throw an error if not found

					set = True
				except Exception as e:
					try: #use to check if page is last page and next page is beginning of next r2
						found = re.search('Page (..) of (..)', data2, re.DOTALL)
						if (found.group(1).isdigit()):
							print('hiii')
							page1 = found.group(1)
							page2 = found.group(2)
							if page1 == page2:
								subprocess.call(['pdftotext',filename,'o2.txt','-f',str(i + 2),'-l',str(i + 2)])
								data2 = ''
								with open('o2.txt', 'r') as myfile:
								   	data2=myfile.read()
								found = re.search('Appropriation/Budget Activity(.+?)UNCLASSIFIED',data2, flags=re.DOTALL).group(1)
								set = True
					except Exception as e:
						continue


		workfile.close()
		print(count)



# data = return_data(112,113,'afd2018.pdf')
# group1, group2 = return_R2_metadata(data)
# print(group1)
# print(group2)
# found = re.search('\(Number/Name\)\s(.+?)(PE.+?)Prior',data, re.DOTALL)
# print(found.group(1))
# print(found.group(2))


write_page_text(1,430,filename='afd2018.pdf')

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


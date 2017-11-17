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
def return_row_names(string, early_pdf=False):
	try:
		found = re.search("(Total\nCost|Program Element)(.+?)(A\.|Note|MDAP|Program)",string,flags=re.DOTALL)
		#print(found.group1)
		group = found.group(1)
		#print('group')
		group = group.split("\n")
	except Exception as e:
		print(string)
		print(e)
	
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
	if year <= 2011: #Col names are different for old docs
		col_list = ['FY ' + str(year-1) + ' Actual']
		for i in range(year, year+6):
			col_list.append('FY ' + str(i) + ' Estimate')
	else:
		if year < 2014:
			col_list = []
		else:
			col_list = ["Prior Years"]
		for i in range(year-1, year+6):
			s = "FY " + str(i)
			if i == year+1:
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
def extract_table(rows,text,year=2018, page=0, filename=''): 
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
			row = rows[i].replace('\n', ' ')
			table_dict[row] = dictionary
			try:
				table_dict[row].update(get_item_desc(rows[i], page,text,filename))
			except Exception as e:
				#print(e)
				print("Cannot find descs")
	except Exception as e:
		print(e)
		print("Table could not be parsed.")
	return a, table_dict

def search_for_desc(desc):
	found = re.search('(A. Mission Description and Budget Item Justification|\(U\) Mission Description| Mission Description)(.+?)(\(U\)|Project|R\-1 Shopping|PE 0|B. Program|B. Accomplishments)', desc, re.DOTALL)
	return found.group(2)


def parse_year_from_filename(filename):
	data2 = return_data(0,0,filename,without_layout=True)
	try:
		found = re.search('Fiscal Year \(FY\) (....)',data2, re.DOTALL).group(1)
		return int(found)-1
	except Exception as e:
		data2 = return_data(180,180, filename, without_layout=False) #Arbitrary page number, but should be far enough in document to get reliable date
		found = re.search('(January|February|March|April|May|June|July|August|September|October|November|December) ([0-9]+)\n',data2, re.DOTALL)
		return int(found.group(2))


def return_data(page1, page2, filename,without_layout=False):
	if not without_layout:
		subprocess.call(['pdftotext',filename,'o2.txt','-layout','-f',str(page1 + 1),'-l',str(page2 + 1)])
	else:
		subprocess.call(['pdftotext',filename,'o2.txt','-f',str(page1 + 1),'-l',str(page2 + 1)])

	data2 = ''
	with open('o2.txt', 'r') as myfile:
		data2=myfile.read()
	return data2

def return_R2_metadata(data,early_pdf=False):
	if not early_pdf:
		#found = re.search('\(Number/Name\)\s(.+?)(PE.+?)Prior',data, re.DOTALL)
		found = re.search('(\(Number/Name\)|NOMENCLATURE)\s(.+?)(PE.+?)(Prior|All|FY)',data, re.DOTALL)
		appropriation = found.group(2).strip()
		program_element = found.group(3)
		if '\n' in program_element:
			appropriation += ' ' + program_element.split('\n')[1]
			program_element = program_element.split('\n')[0]
		return appropriation, program_element
	else:
		found = re.search('PE NUMBER AND TITLE\n\n(.+?)\n\n(.+?)\n',data, re.DOTALL)
		return found.group(1), found.group(2)

def pre_2010(page1,page2,filename=''): 
	data = return_data(page1,page2,filename,without_layout=False)

	found = re.search('Complete(.+?)\n(In|Note|\(U\)|This|THIS)',data, re.DOTALL)
	pattern = re.compile('([0-9]*)[ ]+([A-Za-z\(\)\-\/\& ]+)([0-9].+?)\n', re.DOTALL)
	text = found.group(0)
	#print(text)
	table_dict = {}


	for group in re.findall(pattern,text):
		#print(group)
		if (len(group) > 3):
			group = group[:0] + group[2:] 
		group0 = group[0]
		if group[0] != '':
			group0 = group0 + ' '
		table_dict[group0 + group[1].strip()] = parse_table_string(group[2],parse_year_from_filename(filename))
	print(table_dict)
	return table_dict

def get_item_desc(item, page, data, filename):
	found = re.search('Page (.|..) of (.|..)', data , re.DOTALL)
	pageNo = found.group(2)
	#print(pageNo)
	orig_item = item
	try:
		num = re.search('\s*([0-9]+):', item, re.DOTALL)
		item = num.group(1)
	except Exception as e:
		return ''

	full_data = return_data(page+1, page + int(pageNo), filename, without_layout=True)
	#print(full_data)
	find_desc = re.search(item + '.+?A\.\sMission\sDescription\sand\sBudget\sItem\sJustification(.+?)(B\.\sAccomplishments|B\.\sProgram)', full_data.replace('\n', ' '), re.DOTALL).group(1).replace('\n',' ')
	#print("Desc:" + find_desc)
	return {'Budget Item Description' : find_desc}

def get_plans(page, filename, data):
	found = re.search('Page (.|..) of (.|..)', data, re.DOTALL)
	pageNo = found.group(2)
	#print(pageNo)
	full_data = return_data(page, page + int(pageNo)-1, filename, without_layout=True)
	year = parse_year_from_filename(filename)
	#print(full_data)
	#print(year)
	pattern = re.compile('le:(.+?)\n.+?Description: (.+?)FY ' + str(year-1) + ' Accomplishments:(.+?)FY ' + str(year) + ' Plans:(.+?)FY ' + str(year+1) + ' Plans:(.+?)(Tit|Accomplishments)',re.DOTALL)
	R2_list = []
	for m in re.findall(pattern, full_data):
		table_dict = {}
		#print('hi')
		count = year-1
		clean_data = ''
		table_dict['Title'] = m[0]
		for group in m:
			#print(i)
			#sprint(group + "hi")
			if group == 'Tit' or group == 'Accomplishments' or group == m[0]:
				continue
			elif group == m[1]:
				table_dict['Description'] = group.replace('\n',' ')
				continue
			if 'UNCLASSIFIED' in group:
				pattern2 = re.compile('(.+?)PE.+?C\. Accomplishments/Planned Programs \(. in Millions\)(.+?)FY',re.DOTALL)
				found = re.search(pattern2, group)
				clean_data = found.group(1) + found.group(2)
				#print(clean_data + "HMM")
				#print(found.group(1) + found.group(2))
			else:
				#print('')
				clean_data = group
				#print(clean_data + "hi")
			if count == year-1:
				table_dict[str(count) + ' Accomplishments'] = clean_data.replace('\n',' ')	
			else:
				table_dict[str(count) + ' Plans'] = clean_data.replace('\n',' ')
			count = count + 1
			
		R2_list.append(table_dict)
	return R2_list



"""
Writes a given page's text to a an output file. This file can later be read from and stored as JSON.
@param page1: page to start reading PDF from
@param page2: page to end reading PDF from
@param filename: filename of PDF to convert
"""
def write_page_text(page1, page2,filename='', write_file='newfile.txt', path_dir='',early_pdf=False):
	#Still have to account for files coming from years 2011 (possibly 2010) to 2013
	import os
	import json
	print(filename)
	with open(os.getcwd() + '/' + path_dir + '/' + write_file, 'w') as workfile:
		set = False #bool to help decide which pages should be searched
		count = 0
		for i in range(page1,page2):
			if (set):
				count += 1
				set = False
				data = return_data(i,i,filename,without_layout=False)
				table_dict = {}
				if not early_pdf:
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

					s, table_dict = extract_table(rows,data,year=parse_year_from_filename(filename), page=i,filename=filename)
				else:
					try:
						table_dict = pre_2010(i,i, filename)
					except Exception as e:
						print(e)
						print('Cannot get table')
					#print(table_dict)
					
				try: 
					subprocess.call(['pdftotext',filename,'o.txt','-layout','-f',str(i + 1),'-l',str(i + 1)]) #this could possibly be improved (don't need to call twice)
					data = ''
					with open('o.txt', 'r') as myfile:
				   		data=myfile.read().replace('\n', '')
					table_dict['A. Mission Description and Budget Item Justification'] = search_for_desc(data)
					if early_pdf:
						appropriation, program_element = return_R2_metadata(return_data(i,i,filename, without_layout=True),early_pdf)
					else:
						appropriation, program_element = return_R2_metadata(return_data(i,i,filename, without_layout=False),False)
					table_dict['Appropriation/Budget Activity'] = appropriation
					table_dict['R-1 Program Element (Number/Name)'] = program_element
					try:
						table_dict['Accomplishments/Planned programs'] = get_plans(i, filename, return_data(i,i,filename,without_layout=True))
					except:
						print("Cannot get plans")	
				except Exception as e:
					print(e)
					#print(repr(return_data(i,i,filename,without_layout=True)))
					print("cannot extract desc")

				json.dump(table_dict, workfile)
				workfile.write(',\n')
				#workfile.write(str(table_dict))
				#workfile.write('\n')
				
			else:
				# subprocess.call(['pdftotext',filename,'o2.txt','-f',str(i + 1),'-l',str(i + 1)])
				# data2 = ''
				# with open('o2.txt', 'r') as myfile:
			 	#   			data2=myfile.read()
				data2 = return_data(i,i,filename,without_layout=True)
				try: 
					found = re.search('THIS PAGE(.+?)LEFT BLANK', data2, re.DOTALL)
					found.group(1) #Will throw an error if not found

					set = True
				except Exception as e:
					try: #use to check if page is last page and next page is beginning of next r2
						found = re.search('Page (..) of (..)', data2, re.DOTALL)
						if (found.group(1).isdigit()):
							page1 = found.group(1)
							page2 = found.group(2)
							if page1 == page2:
								subprocess.call(['pdftotext',filename,'o2.txt','-f',str(i + 2),'-l',str(i + 2)])
								data2 = ''
								with open('o2.txt', 'r') as myfile:
								   	data2=myfile.read()
								if not early_pdf:
									found = re.search('Appropriation/Budget Activity(.+?)UNCLASSIFIED',data2, flags=re.DOTALL).group(1)
								else:
									found = re.search('A\.(.+?)Desc',data2, flags=re.DOTALL).group(1)
								set = True
					except Exception as e:
						continue


		workfile.close()



# data = return_data(112,113,'afd2018.pdf')
# group1, group2 = return_R2_metadata(data)
# print(group1)
# print(group2)
# found = re.search('\(Number/Name\)\s(.+?)(PE.+?)Prior',data, re.DOTALL)
# print(found.group(1))
# print(found.group(2))


"""
Writes files from a given 
"""
def write_from_dir(dirname, target_dir=''):
	import os
	file_list = os.listdir(dirname)
	from PyPDF2 import PdfFileReader
	print(file_list)
	for file in file_list:
	#	try:
	#		if (parse_year_from_filename(dirname + '/' + file) < 2009):
				#continue
		#except Exception as e:
		orig_name = file
		#sfile = dirname + '/' + file
		early_pdf = False
		try:
			pdf = PdfFileReader(open(dirname + '/' + file,'rb'))
			num_pages = pdf.getNumPages()
			year = parse_year_from_filename(dirname + '/' + file)
			if year < 2010:
				early_pdf = True
		except Exception as e:
			print(e)
			print("Can't get num pages. Setting default to 500")
			num_pages = 500
		write_file = orig_name.split('.')[0]
		write_file += 'new.json'
		write_page_text(1, num_pages-1, filename=os.getcwd() + '/' + dirname + '/' + file, write_file=write_file, path_dir=target_dir,early_pdf=early_pdf)

		
		
#write_page_text(1,500,filename='R2s/AFD-160208-050.pdf',path_dir='.')

#pre_2010(44,44, '/home/jmkovachi/PDF_extractor/R2s/AFD-070207-030.pdf')
# data = return_data(64,64,'/home/jmkovachi/PDF_extractor/R2s/AFD-070223-063.pdf',without_layout=False)
# print(repr(data))
#data = return_data(337,338,'/home/jmkovachi/PDF_extractor/R2s/AFD-150309-010.pdf',without_layout=True)

#print(data)
#print(get_plans(337,'/home/jmkovachi/PDF_extractor/R2s/AFD-150309-010.pdf', data))

#write_page_text(1,500,'/home/jmkovachi/PDF_extractor/R2s/AFD-150309-009.pdf','test.txt')

# found = re.search('Complete(.+?)\nIn',data, re.DOTALL)
# pattern = re.compile('([0-9]*)[ ]+([A-Za-z\(\)\-\/\& ]+)([0-9].+?)\n', re.DOTALL)
# text = found.group(0)
# for m in re.finditer(pattern, text):
# 	print(parse_table_string(m.group(3),2003))
#     #print (m.group(3))
# print(found.group(0))


#print('hi')

write_from_dir('R2s', target_dir='/target_dir')

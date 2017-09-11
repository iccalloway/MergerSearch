"""
    INPUT: input_file, database, output_folder, merger_set
    
    Note:   Use "|" to separate segment sequences
            Use "." to indicate shared sets of segments
            Use "-" to indicate segments containing the same number of '-' must be identical
"""
import itertools, re, os, sys, sqlite3

##Settings
special_tokens = "./special.txt"
input_file = "words.sqlite"
delim = "-"
safe_separator = " @"
ignore_stress = True
    
import csv
def write_list_to_csv(header, item, output, index):
    with open(output+".csv", "wb") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in item:
            writer.writerow(list(row)[:index]+[sorted(list(a)) for a in row[index]])
    return
    
def read_special_file():
    with open(special_tokens, "r") as f:
        lines = {line.strip().split(" ", 1)[0]:(line.strip().split(" ", 1)[-1]).split(" ") for line in f.readlines() if line.strip()!="" or (len(line.strip())>0 and line[0] !="#")}
    return lines

if __name__ == "__main__":
    if len(sys.argv) == 3:
        flags = None
        output_folder = sys.argv[1]
        merger_list = sys.argv[2].split("|")
    else:
        print ("Invalid syntax - merger-search.py output_folder merger_list")
        exit()

    ## check if input file exists
    if not os.path.isfile(input_file):
        print("No file with name '"+input_file+"'at this location")
        exit()
    
    ## Read in file containing natural classes
    class_dict = read_special_file()
    classes = class_dict.keys()
    
    process_list = [merger_list]
    all_partitions = list(set(re.findall(''+delim+'+'," ".join(merger_list))))
    together = safe_separator.join(merger_list)
    
    ##Intersection segment sets
    intersection=re.findall('\[[\w\s]+\]', together)
    final_intersection = []
    for a in range(len(intersection)):
        expanded_intersection = set([])
        started = False
        for segment in intersection[a][1:-1].split(" "):
            if segment in classes:
                new_segment = set(class_dict[segment])
            else:
                print("'"+segment+"' was not found in feature list.")
                exit()
            if started:
                expanded_intersection.intersection_update(new_segment)
            else:
                started=True
                expanded_intersection.update(new_segment)
        final_intersection.append(list(expanded_intersection))
    for a in range(len(intersection)):
        together = re.sub(re.escape(intersection[a])+"(?![^(]*\))", "("+" ".join(final_intersection[a])+")",together)
        together = re.sub(re.escape(intersection[a])+"(?=[^(]*\))", " ".join(final_intersection[a]),together)
        #together = re.sub(re.escape(intersection[a]), "("+" ".join(final_intersection[a])+")", together, count=1)
    
    ##sames=[re.findall('([A-Za-z]+(?='+delim+'(?: |$)))', together) for delim in all_partitions]
    sames=[re.findall('\([\w\s]+\)(?='+delim+'(?: |$))|[A-Za-z]+(?='+delim+'(?: |$))', together) for delim in all_partitions]
    replacements = []
    
 
    ## For items that must be the same/be different
    for item in sames:
        viable_segments = set([])
        started = False 
        for segment in item:
            if segment[0] == "(":
                segment_set = set([])
                for item in segment[1:-1].split(" "):
                    if item in classes:
                        segment_set.update(set(class_dict[item]))
                    else:
                        segment_set.add(item)    
                if started:
                    viable_segments.intersection_update(segment_set)
                else:
                    viable_segments.update(segment_set)
                    started=True
            else:
                if segment in classes:
                    ##Throw out input not in dictionary
                    if started:
                        viable_segments.intersection_update(set(class_dict[segment]))
                    else:
                        viable_segments.update(set(class_dict[segment]))
                        started=True
                else:
                    if started:
                        viable_segments.intersection_update(set([segment]))
                    else:
                        viable_segments.update(set([segment]))
                        started=True
        replacements.append(list(viable_segments))
    
    possibilities = list(itertools.product(*replacements))
    
    successful_possibilities = []
    for a in range(len(possibilities)):
        if len(possibilities[a]) == len(set(possibilities[a])):
                successful_possibilities.append(possibilities[a])
    
    ## For items that don't need to match/be different
    ##anys=re.findall('[A-Za-z]+(?![A-Za-z]*'+delim+')', together)
    anys=re.findall('\([A-Za-z ]+\)(?!'+delim+')|[A-Za-z]+(?![^(]*\))(?![A-Za-z]*'+delim+')', together)
    any_segments = []
    for segment in anys:
        if segment[0] == "(":
                segment_set = set([])
                for item in segment[1:-1].split(" "):
                    if item in classes:
                        segment_set.update(set(class_dict[item]))
                    else:
                        segment_set.add(item)
                any_segments.append(list(segment_set))
        else:
            if segment in classes:
                any_segments.append(class_dict[segment])
            else:
                any_segments.append([segment])
                
    print anys
    print any_segments
                    
    ## Turn class sets to sets with individual segments    
    final_list = []
    if len(sames)==0:
        for item in itertools.product(*any_segments):
            new=together
            for a in range(len(anys)):
                new = re.sub(re.escape(anys[a])+"(?=$| )", item[a], new, 1)
            final_list.append(new.split(safe_separator))
    elif len(sames)>0 and len(successful_possibilities)>0:
        for solution in successful_possibilities:
            new = together
            for a in range(len(all_partitions)):
                new = re.sub('\(?[A-Za-z ]+\)?'+all_partitions[a]+"(?=$| )", solution[a], new)
            for item in itertools.product(*any_segments):
                temp_new = new
                for i in range(len(anys)):
                    temp_new = re.sub(re.escape(anys[i])+"(?=$| )", item[i], temp_new, 1)
                final_list.append(temp_new.split(safe_separator))
    else:
        print "No possible segment sequences fit your specifications."
        exit()

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    ## Open SQLite Database
    conn = sqlite3.connect(input_file)
    c = conn.cursor()
    
    if len(final_list) > 1:
        combined_answers=[]
    else:
        combined_answers=None
    
    while len(final_list)!=0:
        target = final_list.pop(0)
        final_answers = []
        
        ## Make query to database
        if len(target) > 0:
            first_line_list=["SELECT Table0.same, Table0.word"]
            query_list=["""FROM (SELECT words.* FROM words WHERE merged = '"""+target[0]+"""') Table0"""]
            if len(target) > 1:
                for a in range(1, len(target)):
                    first_line_list.append("Table"+str(a)+".word")
                    query_list.append("""LEFT JOIN (SELECT words.* FROM words WHERE merged = '"""+target[a]+"""') Table"""+str(a)+""" ON Table"""+str(a)+""".same = Table"""+str(a-1)+""".same""")
                query_list.append("WHERE Table"+str(a)+".word IS NOT NULL;")
            first_line = ", ".join(first_line_list)
            query_list.insert(0,first_line)
            full_query = "\n".join(query_list)
            c.execute(full_query)
            
            ## Process answers
            answers = c.fetchall()
            answer_dict = {}
            for item in answers:
                if str(item[0]) not in answer_dict:
                    answer_dict[item[0]] = [set([str(variant)]) for variant in item[1:]]
                else:
                    for a in range(1, len(item)):
                        answer_dict[item[0]][a-1].add(str(item[a]))
            final_answers = sorted(answer_dict.items())
            if combined_answers != None:
                combined_answers= combined_answers+[[target]+list(item) for item in final_answers]
        ## Print / Write answers
        print_name = "|".join(target)
        if len(final_answers)!=0:
            print "Number of groups found for '"+print_name+"': "+str(len(final_answers))
            header = ["SharedSegment(s)"]+target
            output_name = "~".join(target)
            write_list_to_csv(header, final_answers, output_folder+"/"+output_name, 1)
        else:
            continue
            ##print "No groups found for '"+print_name+"'"
    ## Close Database
    conn.close()
    if combined_answers != None:
        header = ["SharedSegment(s)"]+merger_list
        write_list_to_csv(["MergedSegments"]+header, combined_answers, output_folder+"/combined_results", 2)

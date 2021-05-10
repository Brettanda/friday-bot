import json
import os

# from nltk import word_tokenize
# from nltk.tokenize.treebank import TreebankWordDetokenizer

direc = r"E:\Users\Brett\Downloads\Friday"
intents = f"{direc}\\intents"
entities = f"{direc}\\entities"

new = []
ent = []


def run():
  for filename in os.listdir(intents):
    if filename.endswith(".json"):
      if "_usersays" not in filename:
        filen = "".join(filename.split(".json"))
        main = ""
        pat = ""
        try:
          main = intents + "\\" + filen + ".json"
          pat = intents + "\\" + filen + "_usersays_en.json"

          with open(main, encoding="utf8") as f:
            main = json.load(f)
          with open(pat, encoding="utf8") as f:
            pat = json.load(f)
          try:
            responses = main["responses"][0]["messages"][0]["speech"]
          except BaseException:
            responses = ""

          outgoingContext = main["responses"][0]["affectedContexts"] or []

          if "- Positive" in main["name"]:
            sentiment = 1
          elif "- Negative" in main["name"]:
            sentiment = -1
          else:
            sentiment = 0

          patterns = []
          for item in pat:
            pattern = []
            # replace = {
            #     "you": "u",
            #     "you're": "you are",
            #     "don't": "do not",
            #     "for": "4",
            #     "thank you": "thanks",
            #     "thanks": "thank you",
            #     "im": "i am",
            #     "i'm": "I am",
            #     "are": "r",
            #     "wtf": "what the fuck",
            #     "idk": "I don't know"
            # }
            for i in item["data"]:
              i.pop('userDefined', None)
              # i.pop('alias', None)
              # del i['userDefined']
              # del i['alias']
              # i = i.pop("userDefined", None)
              pattern.append(i)
              # for text in i:
              #   test = True
              #   for r in replace:
              #     lower = word_tokenize(i["text"].lower())
              #     if r in lower and test:
              #       x = lower.index(r)
              #       lower[x] = replace[r]
              #       test = False
              #     detoken = TreebankWordDetokenizer().detokenize(lower)
              #     if detoken.find(" .") != -1:
              #       detoken = detoken.replace(" .", ".")
              #     if not test and i["text"].lower() != detoken:
              #       patterns.append()

            # for r in replace:
            #   if r in lower:
            #     x = lower.index(r)
            #     lower[x].replace(r,replace[r])
            #     patterns.append({"text":" ".join(lower)})
            # if "you" in lower:
            #   patterns.append([{"text": lower.replace(" you ", " u ")}])
            # if "you're" in lower:
            #   patterns.append([{"text": lower.replace("you're", "you are")}])
            # if "don't" in lower:
            #   patterns.append([{"text": lower.replace("don't", "do not")}])
            # if "for" in lower:
            #   patterns.append([{"text": lower.replace(" for ", " 4 ")}])
            # if "thank you" in lower:
            #   patterns.append([{"text": lower.replace(" thank you ", " thanks ")}])
            # if "im" in lower:
            #   patterns.append([{"text": lower.replace(" im", " i am")}])
            # if lower.startswith("im"):
            #   patterns.append([{"text": lower.replace("im", "i am", 1)}])
            # if "i'm" in lower:
            #   patterns.append([{"text": lower.replace("i'm", "i am")}])
            # if "are" in lower:
            #   patterns.append([{"text": lower.replace(" are ", " r ")}])
            # if "you" in lower and " are " in lower:
            #   patterns.append([{"text": lower.replace(" you ", " u ").replace(" are ", " r ")}])
            # # if "wtf" in lower:
            # #   patterns.append([{"text": lower.replace(" wtf ", " what the fuck ")}])
            # # if "idk" in lower:
            # #   patterns.append([{"text": lower.replace(" idk ", " i don't know ")}])
            # # if "idk" in lower:
            # #   patterns.append([{"text": lower.replace(" idk ", " i don't know ")}])
            # if i["text"] != lower:
            #   patterns.append([{"text": lower}])
            # if i["text"] != i["text"].capitalize():
            #   patterns.append([{"text": i["text"].capitalize()}])
            patterns.append(pattern)

          # for pat in patterns:
          #   new_pat = []
          #   for item in pat:
          #     lower = word_tokenize(item["text"].lower())
          #     for r in replace:
          #       if r in lower:
          #         x = lower.index(r)
          #         lower[x] = replace[r]
          #         detoken = TreebankWordDetokenizer().detokenize(lower)
          #         if detoken.find(" .") != -1:
          #           detoken = detoken.replace(" .", ".")
          #         if "alias" in item and "meta" in item:
          #           new_pat.append({"text": detoken, "meta": item["meta"], "alias": item["alias"]})
          #         else:
          #           new_pat.append({"text": detoken})
          #   if new_pat != pat and len(new_pat) > 0:
          #     patterns.append(new_pat)

          new.append({
              "tag": main["name"],
              "sentiment": sentiment,
              "priority": main["priority"],
              "patterns": patterns,
              "responses": responses,
              "incomingContext": main["contexts"],
              "outgoingContext": outgoingContext
          })

          for pat in patterns:
            if len(pat):
              x = [i["text"] for i in pat]
              # e = [i["text"] for i in pat if "meta" in i]
              string = "".join(x)
              ents = []
              for y in pat:
                if "meta" in y:
                  word = y["text"]
                  start = string.index(word)
                  end = start + len(word) - 1
                  ents.append((int(start), int(end), y["meta"]))
              # print(f"{finds} {end} - {string[int(finds)]} {string[int(end)]}")
              # print(e)
              # print(string)
              ent.append((
                  string,
                  {"entities": ents}
              ))

        except FileNotFoundError:
          pass
        except KeyError:
          pass

  used_patterns = 0
  patterns = 0
  for intent in new:
    if intent['priority'] > -1:
      used_patterns += len(intent['patterns'])
    patterns += len(intent['patterns'])

  print(f"Number of intents: {len(new)}")
  print(f"Used intents: {len([i for i in new if i['priority'] > -1])}")
  print(f"Pattern count: {patterns}")
  print(f"Used pattern count: {used_patterns}")

  with open("ml/intents.json", "w") as f:
    f.write(json.dumps(new, indent=2, sort_keys=False))
    f.close()

  with open("ml/entities.json", "w") as f:
    f.write(json.dumps(ent, indent=2, sort_keys=False))
    f.close()


if __name__ == "__main__":
  run()

# const edite = [];
# fs.readdir(entities, (err, files) => {
#   if (err) return console.log("Unable to scan directory: " + err);

#   files.map(file => {
#     if (file.includes("_entries")) return;
#     file = file.split(".json").join("");
#     let main, pat;
#     try {
#       main = require(`${entities}${file}.json`);
#       pat = require(`${entities}${file}_entries_en.json`);
#     } catch (err) {
#       return console.error(err);
#     }
#     const entries = pat.map(entry => {
#       return entry;
#     });

#     edite.push({
#       tag: main.name,
#       isEnum: main.isEnum,
#       isRegexp: main.isRegexp,
#       entries: entries,
#     });
#   });
#   fs.writeFileSync("entities.json", JSON.stringify(edite, null, 2));
# });

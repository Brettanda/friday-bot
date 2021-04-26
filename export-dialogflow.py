import json
import os

direc = r"E:\Users\Brett\Downloads\Friday"
intents = f"{direc}\\intents"
entities = f"{direc}\\entities"

new = []


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
            pattern = ""
            for i in item["data"]:
              pattern += i["text"]
            lower = pattern.lower()
            if " you " in lower:
              patterns.append(lower.replace(" you ", " u "))
            if "you're" in lower:
              patterns.append(lower.replace("you're", "you are"))
            if "don't" in lower:
              patterns.append(lower.replace("don't", "do not"))
            if " for " in lower:
              patterns.append(lower.replace(" for ", " 4 "))
            if "thank you" in lower:
              patterns.append(lower.replace(" thank you ", " thanks "))
            if " im" in lower:
              patterns.append(lower.replace(" im", " i am"))
            if lower.startswith("im"):
              patterns.append(lower.replace("im", "i am", 1))
            if "i'm" in lower:
              patterns.append(lower.replace("i'm", "i am"))
            if " are " in lower:
              patterns.append(lower.replace(" are ", " r "))
            if " you " in lower and " are " in lower:
              patterns.append(lower.replace(" you ", " u ").replace(" are ", " r "))
            if " wtf " in lower:
              patterns.append(lower.replace(" wtf ", " what the fuck "))
            if " idk " in lower:
              patterns.append(lower.replace(" idk ", " i don't know "))
            if " idk " in lower:
              patterns.append(lower.replace(" idk ", " i don't know "))
            if pattern != lower:
              patterns.append(lower)
            if pattern != pattern.capitalize():
              patterns.append(pattern.capitalize())
            patterns.append(pattern)

          new.append({
              "tag": main["name"],
              "sentiment": sentiment,
              "priority": main["priority"],
              "patterns": patterns,
              "responses": responses,
              "incomingContext": main["contexts"],
              "outgoingContext": outgoingContext
          })
        except BaseException:
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

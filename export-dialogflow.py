import json
import os

direc = r"C:\Users\brett\downloads\Friday"
intents = f"{direc}\intents"
entities = f"{direc}\entities"

new = []

def run():
  for filename in os.listdir(intents):
    if filename.endswith(".json"):
      if "_usersays" not in filename:
        filen = "".join(filename.split(".json"))
        main = ""
        pat = ""
        try:
          main = intents+"\\"+filen+".json"
          pat = intents+"\\"+filen+"_usersays_en.json"

          with open(main,encoding="utf8") as f:
            main = json.load(f)
          with open(pat,encoding="utf8") as f:
            pat = json.load(f)
          try:
            responses = main["responses"][0]["messages"][0]["speech"]
          except:
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
            patterns.append(pattern)

          new.append({
            "tag":main["name"],
            "sentiment":sentiment,
            "priority":main["priority"],
            "patterns":patterns,
            "responses":responses,
            "incomingContext":main["contexts"],
            "outgoingContext":outgoingContext
          })
        except:
          pass

  print(f"Number of intents added: {len(new)}")

  with open("ml/intents.json","w") as f:
    f.write(json.dumps(new,indent=2,sort_keys=False))
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

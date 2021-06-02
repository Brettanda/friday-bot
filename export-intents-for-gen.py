from numpy import random
import json

with open("ml/current_intents.json") as f:
  intents = json.load(f)

  human = []
  robot = []
  human_count = 0
  robot_count = 0
  print(len([intent["tag"] for intent in intents if intent["priority"] < 0 and type(intent["responses"]) == list]))
  for intent in intents:
    if type(intent["responses"]) == list and len(intent["responses"]) > 0 and intent['priority'] > 0:
      for pattern in intent["patterns"]:
        pattern = "".join([pat["text"] for pat in pattern])
        pattern = pattern.replace("\n", "")
        human.append(pattern)
        human_count += 1
      intent_count = len(intent["patterns"])
      response_count = len(intent["responses"])
      tag = intent["tag"]
      x = 0
      for response in intent["responses"]:
        if x < intent_count:
          robot.append(response)
          x += 1
          robot_count += 1
      if intent_count != response_count and intent_count > response_count:
        for _ in range(intent_count - response_count):
          robot.append(random.choice(intent["responses"]))
          robot_count += 1
    if human_count != robot_count:
      print(intent["tag"])

  print(human_count)
  print(robot_count)

  with open("ml/intent_human.txt", "w", encoding='utf-8') as h:
    h.write("\n".join(human))
    h.close()

  with open("ml/intent_robot.txt", "w", encoding='utf-8') as r:
    r.write("\n".join(robot))
    r.close()
  f.close()

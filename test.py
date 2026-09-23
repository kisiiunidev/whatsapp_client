import requests as req

def test():
  one = req.post("http://localhost:5000/send", json={"recipient": "Eliezer Kitendawili", "message": "Good afternoon server1!"})
  return one.text

try:
  print(test())
except:
  print("Error caught!")
def testing(message):
    print message

testing("message test")


class thing(object):

    def __init__(self):
        print "I am...\n"

    def say(self, message):
        print message

thing().say("working!")

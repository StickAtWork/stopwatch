from random import choice
from string import ascii_lowercase

VOWS = 'aeiouy'
CONS = ''.join(x for x in ascii_lowercase if x not in VOWS)
NUMS = ''.join(str(y) for y in range(10))
SYMS = '!@#$%^&*()'

def random_password():
    """Returns a random password.
    
    Used to set a new user up with a password automatically
    so that the creator doesn't know what it is. The goal is
    to have the server email the new user with their password.
    """
    password = ''
    while len(password) < 6:
        if len(password) % 2:
            password += choice(VOWS)
        else:
            password += choice(CONS)
    password += choice(NUMS)
    password += choice(SYMS)
    return password
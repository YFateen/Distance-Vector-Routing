
class CTRDecrypt(self):

	def __init__(self, ciphertext):
		self.ciphertext = ciphertext


	def bstrxor(a, b):
       return bytes(x ^ y for (x, y) in zip(a, b))

    # strxor takes two hex strings and returns the xor’d output as a bytestring
   	def strxor(a, b):
       return bstrxor(bytes.fromhex(a), bytes.fromhex(b))


def main():
	print ("hello world!")
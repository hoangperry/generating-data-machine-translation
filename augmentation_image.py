import cv2
import numpy
import random
import multiprocessing as mp
import os
import scipy.ndimage as ndi
import ocrodeg
import matplotlib.pyplot as plt
import glob
from utils import ensure_dir
from multiprocessing.dummy import Pool as ThreadPool


class ImageGenerator(object):

	def __init__(self, image):
		self.image = image

	def __init__(self):
		pass

	def load_img(self, img_path):
		"""
		load image from name
		:param img_path:
		:return:
		"""
		self.image = cv2.imread(img_path, 0)

	def set_img(self, image):
		"""
		set attribute
		:param image:
		:return:
		"""
		self.image = image

	def rotate_image(self, angle):
		"""
		rotate image
		recommend angle: -0.5 to 0.5
		:param angle:
		:return:
		"""

		image_center = tuple(numpy.array(self.image.shape[1::-1]) / 2)
		rot_mat = cv2.getRotationMatrix2D(image_center, angle, 1.0)
		# update img
		self.image = cv2.warpAffine(self.image, rot_mat, self.image.shape[1::-1], flags=cv2.INTER_LINEAR)

	def noisy(self, s_vs_p = 0.5, amount = 0.009):
		"""
		add s&p noise
		:param s_vs_p:
		:param amount:
		:return:
		"""

		num_salt = numpy.ceil(amount * self.image.size * s_vs_p)
		coords = [numpy.random.randint(0, i - 1, int(num_salt)) for i in self.image.shape]
		self.image[coords] = 1

		# Pepper mode
		num_pepper = numpy.ceil(amount * self.image.size * (1. - s_vs_p))
		coords = [numpy.random.randint(0, i - 1, int(num_pepper)) for i in self.image.shape]
		self.image[coords] = 0

	def show_img(self):
		plt.figure(figsize=(90,20))
		plt.imshow(self.image, cmap='gray')

	def blur(self):
		is_blur = bool(random.getrandbits(1))
		is_distor = bool(random.getrandbits(1))

		if is_blur == True:
			s = random.randint(0, 2)
			self.image = ndi.gaussian_filter(self.image, s)

		if is_distor == True:
			sigma = random.uniform(30, 50)
			noise = ocrodeg.bounded_gaussian_noise(self.image.shape, sigma, 5.0)
			self.image = ocrodeg.distort_with_noise(self.image, noise)

	def save_img(self, img_name):
		cv2.imwrite(img_name, self.image)

	def gen(self, rotate=False, noisy=False):

		blur = bool(random.getrandbits(1))

		if noisy == True:
			# random s and p
			s_vs_p = random.uniform(0.3, 0.6)
			# random amount
			amount = random.uniform(0.0002, 0.019)
			self.noisy(s_vs_p = s_vs_p, amount = amount)
		elif rotate == True:
			left_or_right = random.randint(0,1)
			angle = 0
			if left_or_right == 0:
				# left rotate
				angle = random.uniform(-0.5, -0.36)
			else:
				# right
				angle = random.uniform(0.36, 0.5)

			self.rotate_image(angle)
		elif blur == True:
			self.blur()
			pass


class MultiThreadGenerator(object):
	
	def __init__(self, inputdir, outdir):
		self.num_cpus = mp.cpu_count()
		self.outdir = outdir
		self.inputdir = inputdir
		self.processed = 0

	def set_list_files(self, list_files):
		self.list_files = list_files


	def img_gen_func(self, all_files):
		# independency generator
		img_gen = ImageGenerator()

		# all files
		for f in all_files:
			# print dir
			# print(f)
			# load image
			img_gen.load_img(f)

			# add random noise
			# random true or false
			rotate = bool(random.getrandbits(1))
			noisy = bool(random.getrandbits(1))

			img_gen.gen(rotate=rotate, noisy=noisy)

			# save image
			print("\rProcessed " + str(self.processed) + "\tFile", end='')
			save_name = f.replace(self.inputdir[:-1], self.outdir[:-1])

			ensure_dir(os.path.dirname(save_name) + "/")
			img_gen.save_img(save_name)
			self.processed += 1

	def run(self):
		list_len = len(self.list_files)
		num_cpus = self.num_cpus

		print("Total files: ", list_len)
		print("Num CPUs ", num_cpus)

		avg = list_len / num_cpus
		map_params = []
		last = 0.0

		while last < list_len:
			map_params.append(self.list_files[int(last):int(last + avg)])
			last += avg


		pool = ThreadPool(self.num_cpus)
		results = pool.map(self.img_gen_func, map_params)


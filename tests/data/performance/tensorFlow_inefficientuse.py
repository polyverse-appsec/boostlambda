import tensorflow as tf

# Define a simple map function
def map_func(image, label):
    image = tf.cast(image, tf.float32)
    image /= 255
    return image, label

# Load MNIST dataset
mnist = tf.keras.datasets.mnist
(train_images, train_labels), _ = mnist.load_data()

# Construct a tf.data.Dataset
dataset = tf.data.Dataset.from_tensor_slices((train_images, train_labels))

# Inefficient approach: Map function is applied before batching
dataset = dataset.map(map_func)
dataset = dataset.batch(32)

# Print dataset
for image_batch, label_batch in dataset.take(1):
    print("Batch shape:", image_batch.shape)

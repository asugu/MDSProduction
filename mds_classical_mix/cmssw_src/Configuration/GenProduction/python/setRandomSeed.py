import random

def customise(process):
    for name in dir(process.RandomNumberGeneratorService):
        generator = getattr(process.RandomNumberGeneratorService, name)
        if hasattr(generator, "initialSeed"):
            seed = random.randint(0, 2**31)
            print("Setting random seed of %s to %d" % (name, seed))
            generator.initialSeed = seed
    return process


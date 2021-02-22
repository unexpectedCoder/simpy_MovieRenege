from typing import Generator
import collections
import random
import simpy


Theater = collections.namedtuple('Theater',
                                 'counter, movies, available, sold_out, when_sold_out, num_reneges')


def main():
    # Setup and start the simulation
    print("*** Movie Renege ***")
    random.seed(42)
    env = simpy.Environment()

    # Create movie theater
    tickets = 50            # number of tickets per movie
    movies = ['Python Unchained', 'Kill Process', 'Pulp Implementation']
    available = {movie: tickets for movie in movies}
    counter = simpy.Resource(env, capacity=1)
    sold_out = {movie: env.event() for movie in movies}
    when_sold_out = {movie: None for movie in movies}
    num_reneges = {movie: 0 for movie in movies}
    theater = Theater(counter, movies, available, sold_out, when_sold_out, num_reneges)

    # Start process and run
    env.process(customer_arrivals(env, theater))
    env.run(until=120)

    # Analysis/results
    for movie in movies:
        if theater.sold_out[movie]:
            print(f"Movie '{movie}' sold out {theater.when_sold_out[movie]:.1f} minutes "
                  f"after ticket counter opening")
            print(f"\tNumber of people leaving queue when film sold out: {theater.num_reneges[movie]}")

    return 0


def customer_arrivals(env: simpy.Environment, theater: Theater) -> Generator:
    """Create new *moviegoers* until the sim time reaches ``until`` value.

    :param env: The `simpy``'s environment.
    :param theater: The theater's object.
    :return: The ``simpy``'s generator or *None*.
    """
    while True:
        yield env.timeout(random.expovariate(1 / .5))

        movie = random.choice(theater.movies)
        num_tickets = random.randint(1, 6)
        if theater.available[movie]:
            env.process(moviegoer(env, movie, num_tickets, theater))


def moviegoer(env: simpy.Environment, movie, num_tickets: int, theater: Theater) -> Generator:
    """A moviegoer tries to by a number of tickets (``num_tickets``) for a certain ``movie`` in a ``theater``.

    If the movie becomes sold out, she leaves the theater. If she gets
    to the counter, she tries to buy a number of tickets. If not enough
    tickets are left, she argues with the teller and leaves.

    If at most one ticket is left after the moviegoer bought her
    tickets, the *sold out* event for this movie is triggered causing
    all remaining moviegoers to leave.

    :param env: The ``simpy``'s environment.
    :param movie: The movie's ID.
    :param num_tickets: The number of tickets for the movie.
    :param theater: The theater's object.
    :return: The ``simpy``'s generator or *None*.
    """
    with theater.counter.request() as my_turn:
        # Wait until its our turn or until the movie is sold out
        result = yield my_turn | theater.sold_out[movie]

        # Check if it's our turn or if movie is sold out
        if my_turn not in result:
            theater.num_reneges[movie] += 1
            return

        # Check if enough tickets left
        if theater.available[movie] < num_tickets:
            # Moviegoer leaves after some discussion
            yield env.timeout(.5)
            return

        # Buy tickets
        theater.available[movie] -= num_tickets
        if theater.available[movie] < 2:
            # Trigger the "sold out" event for the movie
            theater.sold_out[movie].succeed()
            theater.when_sold_out[movie] = env.now
            theater.available[movie] = 0
        yield env.timeout(1)


if __name__ == '__main__':
    main()

import logging, sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FIXED_FILENAMES = ("b_should_be_easy.in",)
# ("a_example.in", "b_should_be_easy.in", "c_no_hurry.in", "d_metropolis.in", "e_high_bonus.in")
IN_FILENAMES = sys.argv[1].split(",") if len(sys.argv) > 1 else FIXED_FILENAMES
print IN_FILENAMES

DIST_RATIO = float(sys.argv[2]) if len(sys.argv) > 2 else 1
EARLY_RATIO = float(sys.argv[3]) if len(sys.argv) > 3 else 1


class Manager:
    def __init__(self, filename):
        self.step = 0
        self.rides = []
        self.assigned_rides = []
        self.cars = []

        data = open(filename, "rb").read().split("\n")

        # Format context data
        context = map(int, data[0].split(" "))
        self.rows, self.cols, self.num_cars, self.num_rides, self.bonus, self.total_steps = context
        logger.debug(str(self))

        # Format rides data
        logger.debug("Rides:")
        cont = 0
        for line in data[1:-1]:
            ride_data = map(int, line.split(" "))
            start_point = ride_data[:2]
            end_point = ride_data[2:4]
            early_start = ride_data[4]
            latest_finish = ride_data[5]
            ride = Ride(self, cont, start_point, end_point, early_start, latest_finish)
            self.rides.append(ride)
            cont += 1
            logger.debug(ride)

        logger.debug("\nAssigned:")
        # Initialize cars
        self.cars = [Car(self, i) for i in range(self.num_cars)]

        for car in self.cars:
            ride = self.get_ride(car)
            car.assign_ride(ride)

            logger.debug(car)
            logger.debug(ride)

    def get_ride(self, car):
        best_ride = None
        best_score = None

        for ride in self.rides:
            if not self.valid_ride(car, ride):
                continue

            # Calc. of the metric
            curr_score = self.get_score(car, ride)

            if best_score is None or curr_score < best_score:
                best_score = curr_score
                best_ride = ride

        if best_ride is not None:
            self.rides.remove(best_ride)
            self.assigned_rides.append(best_ride)

        return best_ride

    def get_score(self, car, ride):
        dist_score = float(self.distance(car.coords, ride.start))  # / (self.rows + self.cols) / 2.0
        early_score = float(ride.e_start - (self.step + self.distance(car.coords, ride.start)))  # / self.total_steps
        # if early_score < 0:
        #    early_score = 0
        #  + self.distance(car.coords, ride.start)
        return DIST_RATIO * dist_score + EARLY_RATIO * early_score

    def valid_ride(self, car, ride):
        dist_init = self.distance(car.coords, ride.start)
        dist_ride = self.distance(ride.start, ride.end)

        return self.step + dist_init + dist_ride < ride.l_end

    @staticmethod
    def distance(src, dst):
        return abs(src[0] - dst[0]) + abs(src[1] - dst[1])

    def __str__(self):
        return "Context:" + \
               "\nBoard size: (%d, %d)" % (self.rows, self.cols) + \
               "\nNum. cars: %d" % (self.num_cars) + \
               "\nNum. rides: %d" % (self.num_rides) + \
               "\nBonus: %d" % (self.bonus) + \
               "\nMax. steps: %d\n" % (self.total_steps)

    def tick(self):
        for car in self.cars:
            if not car.is_stopped():
                car.tick()

            logger.debug(car)
            logger.debug(car.ride)
        self.step += 1

    def output(self, filename):
        f = open(filename, "wb")

        for car in self.cars:
            f.write(car.output() + "\n")


class Ride:
    def __init__(self, man, id, s, e, es, le):
        self.man = man
        self.id = id
        self.start = s
        self.end = e
        self.e_start = es
        self.l_end = le

    def __str__(self):
        return "%d: [%d, %d] -> [%d, %d], e_start: %d, l_end: %d" % \
               (self.id, self.start[0], self.start[1], self.end[0], self.end[1], self.e_start, self.l_end)


class Car:
    def __init__(self, man, id):
        self.man = man
        self.id = id
        self.ride = None
        self.rides_done = []
        self.coords = [0, 0]
        self.state = "IDLE"  # IDLE, TO_INIT, WAITING, RIDING, STOPPED
        self.curr_steps_len = 0

    def assign_ride(self, ride):
        self.ride = ride

        if self.coords == ride.start:
            self.state = "RIDING"
            self.curr_steps_len = Manager.distance(self.coords, ride.end) - 1
        else:
            self.state = "TO_INIT"
            self.curr_steps_len = Manager.distance(self.coords, ride.start) - 1

    def tick(self):
        if self.curr_steps_len > 0:
            self.curr_steps_len -= 1
        elif self.state == "TO_INIT" and self.man.step < self.ride.e_start:  # == 0
            self.state = "WAITING"
        elif self.state in ("TO_INIT", "WAITING") and self.man.step >= self.ride.e_start:
            self.state = "RIDING"
            self.coords = self.ride.start
            self.curr_steps_len = Manager.distance(self.coords, self.ride.end) - 1
        elif self.state == "RIDING":

            self.rides_done.append(self.ride.id)
            self.coords = self.ride.end

            self.ride = self.man.get_ride(self)

            if self.ride is None:
                self.state = "STOPPED"
            else:
                self.state = "TO_INIT"
                self.curr_steps_len = Manager.distance(self.coords, self.ride.start) - 1

    def is_stopped(self):
        return self.state == "STOPPED"

    def output(self):
        return "%d %s" % (len(self.rides_done), " ".join(map(str, self.rides_done)))

    def __str__(self):
        return "%d: %s(%d, %d), ride: %d, rem_steps: %d" % \
               (self.id, self.state, self.coords[0], self.coords[1], \
                self.ride.id if self.ride else -1, self.curr_steps_len)


for filename in IN_FILENAMES:
    logger.info("----------------------------------------\n")
    logger.info("FILENAME: %s\n" % filename)
    logger.info("----------------------------------------\n")
    m = Manager(filename)

    for step in range(m.total_steps):
        logger.debug("Remaining rides:")
        for r in m.rides:
            logger.debug(r)
        logger.debug("\nTick %d" % step)
        m.tick()

        if all([c.is_stopped() for c in m.cars]):
            break

        if step % 1000 == 0:
            logger.info("\nTick: %d, num_rides: %d" % (step, len(m.rides)))

    m.output(filename.replace(".in", ".out"))

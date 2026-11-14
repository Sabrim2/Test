#include "../src/global.h"
#include "../system/FRFCFS_THRESHOLD/RequestScheduler_FRFCFS_THRESHOLD.h"
#include <cassert>
#include <iostream>

using namespace MCsim;

// Use our real scheduler, but control whether admission succeeds.
class TestScheduler : public RequestScheduler_FRFCFS_THRESHOLD
{
public:
    bool accept;
    Request *lastSelected;

    TestScheduler(
        std::vector<RequestQueue *> &requests,
        std::vector<CommandQueue *> &commands,
        const std::map<unsigned int, bool> &requestors)
        : RequestScheduler_FRFCFS_THRESHOLD(requests, commands, requestors)
    {
        accept = true;
        lastSelected = NULL;
        updateRowTable(0, 0, 10);
    }

    bool isSchedulable(Request *request, bool open) override
    {
        if (!accept)
        {
            return false;
        }

        lastSelected = request;
        return true;
    }
};

int main()
{
    RequestQueue queue(false, false);
    CommandQueue commands(false);

    std::vector<RequestQueue *> requestQueues;
    requestQueues.push_back(&queue);

    std::vector<CommandQueue *> commandQueues;
    commandQueues.push_back(&commands);

    std::map<unsigned int, bool> requestors;
    TestScheduler scheduler(requestQueues, commandQueues, requestors);

    unsigned int rows[8] = {20, 30, 10, 10, 10, 10, 10, 20};
    Request *requests[8];

    for (unsigned int i = 0; i < 8; i++)
    {
        requests[i] = new Request(0, DATA_READ, 64, i * 64, NULL);
        requests[i]->rank = 0;
        requests[i]->bank = 0;
        requests[i]->row = rows[i];

        for (unsigned int j = 0; j < 6; j++)
        {
            requests[i]->addressMap[j] = 0;
        }

        requests[i]->addressMap[Row] = rows[i];
        queue.insertRequest(requests[i]);
    }

    // Failed admission must leave the queue and counters unchanged.
    scheduler.accept = false;

    for (unsigned int i = 0; i < 6; i++)
    {
        scheduler.requestSchedule();
    }

    assert(queue.getSize(false, 0) == 8);
    assert(scheduler.lastSelected == NULL);

    scheduler.accept = true;

    // Four hits, then A, then B.
    unsigned int expected[6] = {2, 3, 4, 5, 0, 1};

    for (unsigned int i = 0; i < 6; i++)
    {
        scheduler.lastSelected = NULL;
        scheduler.requestSchedule();

        assert(scheduler.lastSelected == requests[expected[i]]);
        assert(queue.getSize(false, 0) == 7 - i);

        delete requests[expected[i]];
    }

    // The queue destructor cleans up the two requests still waiting.
    std::cout << "PASS: four-hit limit, retained counts, and stalled attempts\n";
}

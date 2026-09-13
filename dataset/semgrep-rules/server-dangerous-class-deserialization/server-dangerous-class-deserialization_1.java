
package de.mogwailabs.BSidesRMIService;

import java.rmi.Remote;
import java.rmi.RemoteException;

// ok:server-dangerous-class-deserialization
public interface IBSidesServiceOK extends Remote {
   boolean registerTicket(long ticketID) throws RemoteException;
   void vistTalk(long talkID) throws RemoteException;
   void poke(int attende) throws RemoteException;
}
